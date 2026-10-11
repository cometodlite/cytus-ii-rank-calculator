#!/usr/bin/env python3
"""Build a PROPOSED 288-slot roster from audited, source-backed candidate data."""

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
OUTPUT = AUDIT / "roster_proposal_288.csv"
EXCEPTIONS = AUDIT / "roster_proposal_exceptions.csv"
REPORT = AUDIT / "roster_proposal.md"


def read(name):
    with (AUDIT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def norm(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return "".join(ch for ch in value if ch.isalnum())


def level_num(value):
    value = (value or "").strip()
    if not value:
        return None
    if value in {"α", "β", "γ"}:
        return None
    if value[0].isdigit():
        return int(value.rstrip("+")) + (0.5 if value.endswith("+") else 0)
    return None


def get_fact_key(title, difficulty):
    return (norm(title), (difficulty or "").upper())


def numeric(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def structural_signature(desk):
    if not desk or desk.get("desk_review_status") != "DESK_REVIEWED":
        return None
    names = ("click", "hold", "long", "dragh", "drag", "flick", "cdragh", "cdrag")
    counts = [numeric(desk.get(f"snapshot_{n}_count")) for n in names]
    total = sum(counts)
    mix = [x / total for x in counts] if total else [0.0] * len(counts)
    return {
        "mix": mix,
        "avg_density": numeric(desk.get("snapshot_note_density_avg")),
        "peak_density": numeric(desk.get("snapshot_note_density_max")),
        "rhythm_count": numeric(desk.get("snapshot_rhythm_count")),
    }


def composite_distance(a, b, target_level=None, chart_level=None, fallback_density_a=0, fallback_density_b=0):
    """Use archived structure + level proximity; level alone does not pick the substitute."""
    sa, sb = structural_signature(a), structural_signature(b)
    if sa and sb:
        mix_delta = sum(abs(x - y) for x, y in zip(sa["mix"], sb["mix"])) / 2
        density_delta = min(1.0, abs(sa["avg_density"] - sb["avg_density"]) / max(sa["avg_density"], sb["avg_density"], 1.0))
        peak_delta = min(1.0, abs(sa["peak_density"] - sb["peak_density"]) / max(sa["peak_density"], sb["peak_density"], 1.0))
        rhythm_delta = min(1.0, abs(sa["rhythm_count"] - sb["rhythm_count"]) / max(sa["rhythm_count"], sb["rhythm_count"], 1.0))
        structural = 0.45 * mix_delta + 0.25 * density_delta + 0.20 * peak_delta + 0.10 * rhythm_delta
    else:
        structural = min(1.0, abs(fallback_density_a - fallback_density_b) / max(fallback_density_a, fallback_density_b, 1.0))
    ln, cn = level_num(target_level), level_num(chart_level)
    level_gap = min(1.0, abs(ln - cn) / 15) if ln is not None and cn is not None else 0.5
    return 0.65 * structural + 0.35 * level_gap


def main():
    slot_rows = read("chart_slots.csv")
    facts = read("bdct_song_chart_facts.csv")
    standards = read("bdct_standard_4_7_recomposition_candidates.csv")
    dct_candidates = read("dct_candidate_rosters.csv")
    desk_rows = read("chart_desk_review.csv")
    source_discrepancies = read("audit_4_source_discrepancies.csv")
    fact_by_key = {r["chart_key"]: r for r in facts}
    fact_by_song = defaultdict(list)
    for r in facts:
        fact_by_song[r["source_song_key"]].append(r)
    fact_by_title_diff = defaultdict(list)
    for r in facts:
        fact_by_title_diff[get_fact_key(r["song_title"], r["chart_difficulty"])].append(r)
    desk_by_key = {r["candidate_chart_key"]: r for r in desk_rows}

    # Lock the Standard proposal first: preserve grades 1-3 and 8-15; use the
    # audited grade 4-7 easing proposal in its proposed slot order.
    standard_proposal = {(int(r["grade_no"]), int(r["proposed_position"])): r for r in standards}
    b_rows = []
    for source in slot_rows:
        if not source["exam_type"].startswith("B-DCT"):
            continue
        row = dict(source)
        exam = source["exam_type"]
        if exam == "B-DCT Standard" and 4 <= int(source["grade_no"]) <= 7:
            proposal = standard_proposal[(int(source["grade_no"]), int(source["slot_position"]))]
            key = proposal["proposed_chart_key"]
            fact = fact_by_key[key]
            row.update({
                "candidate_source_song_key": key.rsplit("#", 1)[0],
                "candidate_source_title": fact["song_title"], "candidate_chart_key": key,
                "candidate_chart_level": fact["actual_level"], "candidate_unlock_condition": fact["unlock_condition"],
                "candidate_note_count": fact["note_count"], "candidate_bpm": fact["bpm"],
                "candidate_length": fact["length"], "candidate_notes_per_min": fact["notes_per_min"],
                "candidate_source_page": fact["source_url"], "candidate_chart_fact_status": fact["fact_status"],
                "_selection_basis": "4차 승인 없이 후보화: 4~7단 표기 레벨 상승을 완화하는 3차 제안 순서; 1~3단은 변경하지 않음.",
                "_source_slot_id": proposal["original_slot_id"], "_candidate_target": proposal["target_level_for_position"],
                "_source_confidence": fact["source_confidence"], "_source_checked_on": fact["source_checked_on"],
            })
        else:
            row["_selection_basis"] = ("기존 1~3단 곡/차트 추정 유지; 과거 실제 편성 근거는 미확인." if exam == "B-DCT Standard" and int(source["grade_no"]) <= 3
                                        else "감사 기준 현재 슬롯 후보 유지; 출처 메타데이터 기반 제안이며 실전 검증 전.")
            row["_source_slot_id"] = source["slot_id"]
            row["_candidate_target"] = ""
            row["_source_confidence"] = source["source_confidence"]
            row["_source_checked_on"] = source["candidate_source_checked_on"]
        b_rows.append(row)

    # DCT proposals are held intact and reserved before resolving B-DCT exact-chart
    # collisions. These are separate candidates, not formula approvals.
    used_by_exam = defaultdict(set)
    for r in b_rows:
        if r["exam_type"] == "B-DCT Standard":
            used_by_exam[r["exam_type"]].add(get_fact_key(r["candidate_source_title"], r["candidate_chart_key"].rsplit("#", 1)[-1]))
    for r in dct_candidates:
        used_by_exam[r["exam_type"]].add(get_fact_key(r["song_title"], r["chart_difficulty"]))

    # Resolve SV and STT collisions without using level distance as the sole
    # criterion. Standard is retained first because grades 1-3 are user-directed
    # holds and grades 4-7 are the specific requested easing proposal. SV keeps
    # its existing mapping where possible; STT takes an alternative when needed.
    replacement_basis = {}
    for exam in ("B-DCT SV", "B-DCT STT"):
        groups = defaultdict(list)
        for r in sorted((x for x in b_rows if x["exam_type"] == exam), key=lambda x: (int(x["grade_no"]), int(x["slot_position"]))):
            groups[r["candidate_chart_key"]].append(r)
        for old_key, group in groups.items():
            first = group[0]
            old_fact = fact_by_key.get(old_key)
            if not old_fact:
                continue
            owner_key = get_fact_key(old_fact["song_title"], old_fact["chart_difficulty"])
            other_owned = set().union(*(keys for other, keys in used_by_exam.items() if other != exam))
            chosen = old_fact
            basis = "기존 앱 채보 추정을 유지; 교차 유형에서 이 정확한 곡·채보 조합을 사용하지 않음. 시험 목적 적합성은 플레이 전 미확정."
            if owner_key in other_owned:
                same_song = [f for f in fact_by_song[first["candidate_source_song_key"]]
                             if get_fact_key(f["song_title"], f["chart_difficulty"]) not in other_owned
                             and f["chart_key"] != old_key]
                pool = same_song
                if not pool:
                    # Keep completing the proposal: choose another source-confirmed
                    # B-DCT chart, using structural similarity and level proximity.
                    pool = [f for f in facts if get_fact_key(f["song_title"], f["chart_difficulty"]) not in other_owned
                            and f["chart_key"] != old_key]
                if pool:
                    old_desk = desk_by_key.get(old_key)
                    pool.sort(key=lambda f: (
                        0 if f["source_song_key"] == first["candidate_source_song_key"] else 1,
                        composite_distance(old_desk, desk_by_key.get(f["chart_key"]), first["candidate_chart_level"], f["actual_level"],
                                           numeric(first.get("candidate_notes_per_min")), numeric(f.get("notes_per_min"))),
                        f["chart_key"],
                    ))
                    chosen = pool[0]
                    same_song_flag = chosen["source_song_key"] == first["candidate_source_song_key"]
                    basis = ("동일 곡의 출처 확인 채보로 교차 유형의 같은 차트 키를 분리; 표기 레벨과 과거 차트 구조 요약을 함께 비교했으나 SV 점수 안정성은 미검증."
                             if same_song_flag else
                             "동일 곡에 충돌 없는 출처 채보가 없어 다른 출처 확인 차트를 제안; 레벨 근접도와 과거 구조 요약을 함께 비교했으며 SV 목적 적합성은 미검증.") if exam == "B-DCT SV" else (
                        "동일 곡의 출처 확인 채보로 교차 유형의 같은 차트 키를 분리; 표기 레벨과 과거 차트 구조 요약을 함께 비교했으나 STT 정확도 적합성은 미검증."
                        if same_song_flag else
                        "동일 곡에 충돌 없는 출처 채보가 없어 다른 출처 확인 차트를 제안; 레벨 근접도와 과거 구조 요약을 함께 비교했으며 STT 목적 적합성은 미검증.")
            chosen_key = get_fact_key(chosen["song_title"], chosen["chart_difficulty"])
            used_by_exam[exam].add(chosen_key)
            if chosen["chart_key"] != old_key:
                replacement_basis[(exam, old_key)] = (chosen["chart_key"], basis)
            for row in group:
                if chosen["chart_key"] != old_key:
                    row.update({
                        "candidate_source_song_key": chosen["source_song_key"], "candidate_source_title": chosen["song_title"],
                        "candidate_chart_key": chosen["chart_key"], "candidate_chart_level": chosen["actual_level"],
                        "candidate_unlock_condition": chosen["unlock_condition"], "candidate_note_count": chosen["note_count"],
                        "candidate_bpm": chosen["bpm"], "candidate_length": chosen["length"],
                        "candidate_notes_per_min": chosen["notes_per_min"], "candidate_source_page": chosen["source_url"],
                        "candidate_chart_fact_status": chosen["fact_status"], "_source_confidence": chosen["source_confidence"],
                        "_source_checked_on": chosen["source_checked_on"], "_selection_basis": basis,
                        "_source_slot_id": row["slot_id"],
                    })
                else:
                    row["_selection_basis"] = basis

    roster = []
    # Keep actual chart identity separate from the non-official source key.
    for row in b_rows:
        key = row["candidate_chart_key"]
        fact = fact_by_key.get(key, {})
        roster.append({
            "slot_id": row["slot_id"], "source_slot_id": row.get("_source_slot_id", row["slot_id"]),
            "exam_type": row["exam_type"], "grade_no": row["grade_no"], "grade_label": row["grade_label"],
            "slot_position": row["slot_position"], "song_id": "", "source_song_key": row["candidate_source_song_key"],
            "song_title": row["candidate_source_title"], "chart_difficulty": key.rsplit("#", 1)[-1],
            "display_level": row["candidate_chart_level"], "unlock_condition": row["candidate_unlock_condition"],
            "note_count": row["candidate_note_count"], "bpm": row["candidate_bpm"], "length": row["candidate_length"],
            "notes_per_min_proxy": row["candidate_notes_per_min"], "chart_key": key,
            "selection_basis": row.get("_selection_basis", "출처 확인 후보; 실전 적합성은 보류."),
            "source_url": row["candidate_source_page"], "source_checked_on": row.get("_source_checked_on", ""),
            "source_confidence": row.get("_source_confidence", ""), "source_fact_status": row.get("candidate_chart_fact_status", "SOURCE_CONFIRMED"),
            "historical_snapshot_match": desk_by_key.get(key, {}).get("snapshot_match_status", "NO_ARCHIVE_RECORD"),
            "source_discrepancy_status": "UNRESOLVED_REBOOST_CHAOS_11_VS_11_PLUS" if get_fact_key(row["candidate_source_title"], key.rsplit("#", 1)[-1]) == get_fact_key("Re:Boost", "CHAOS") else "NONE_RECORDED",
            "conflict_status": "NONE_CROSS_TYPE", "conflict_with": "", "roster_status": "PROPOSED",
            "playtest_status": "PENDING", "slot_verification_status": "PENDING",
        })

    for row in dct_candidates:
        source_diff = row["chart_difficulty"]
        roster.append({
            "slot_id": row["slot_id"], "source_slot_id": row["slot_id"], "exam_type": row["exam_type"],
            "grade_no": row["grade_no"], "grade_label": row["grade_label"], "slot_position": row["slot_position"],
            "song_id": row["official_song_id"], "source_song_key": row["proposed_source_song_key"],
            "song_title": row["song_title"], "chart_difficulty": source_diff, "display_level": row["actual_level"],
            "unlock_condition": row["unlock_condition"], "note_count": row["note_count"], "bpm": row["bpm"],
            "length": row["length"], "notes_per_min_proxy": row["notes_per_min"], "chart_key": row["candidate_chart_key"],
            "selection_basis": ("3차 감사 DCT 독립 후보 목록에서 목표 레벨 일치 채보를 유지; Standard와 MSTT 간 별도 목록. MSTT 공식 산식·합격선은 적용하지 않음."
                                if row["exam_type"] == "DCT MSTT" else
                                "3차 감사 DCT Standard 독립 후보 목록에서 목표 레벨 일치 채보를 유지; 실전 검증 전."),
            "source_url": row["source_url"], "source_checked_on": row["source_checked_on"],
            "source_confidence": row["source_confidence"], "source_fact_status": row["candidate_status"],
            "historical_snapshot_match": "SEE_CHART_DESK_REVIEW", "source_discrepancy_status": "NONE_RECORDED",
            "conflict_status": "NONE_CROSS_TYPE", "conflict_with": "", "roster_status": "PROPOSED",
            "playtest_status": "PENDING", "slot_verification_status": "PENDING",
        })

    expected = Counter({"B-DCT Standard": 60, "B-DCT SV": 52, "B-DCT STT": 56, "DCT Standard": 60, "DCT MSTT": 60})
    assert len(roster) == 288 and Counter(r["exam_type"] for r in roster) == expected
    # Annotate active exact-chart cross-exam collisions and repeats within one exam.
    chart_owners = defaultdict(list)
    for row in roster:
        chart_owners[row["chart_key"]].append(row)
    exceptions = []
    for chart_key, owners in chart_owners.items():
        types = sorted({r["exam_type"] for r in owners})
        if len(types) > 1:
            conflict_text = " | ".join(types)
            for row in owners:
                row["conflict_status"] = "UNRESOLVED_CROSS_TYPE"
                row["conflict_with"] = conflict_text
            exceptions.append({"exception_type": "CROSS_EXAM_DUPLICATE", "status": "UNRESOLVED",
                               "chart_key": chart_key, "exam_types": " | ".join(types),
                               "affected_slots": " | ".join(r["slot_id"] for r in owners),
                               "detail": "Same exact chart remains proposed in multiple exam types; resolve before final approval."})
        elif len(owners) > 1:
            for row in owners:
                row["conflict_status"] = "INTRA_EXAM_REPEAT"
            exceptions.append({"exception_type": "INTRA_EXAM_REPEAT", "status": "PROPOSED_EXCEPTION",
                               "chart_key": chart_key, "exam_types": types[0],
                               "affected_slots": " | ".join(r["slot_id"] for r in owners),
                               "detail": f"Same chart is repeated {len(owners)} times within one exam type; cross-type prohibition is unaffected, but roster diversity remains for approval."})

    # Any duplicate song/difficulty across different key spellings is still an exact-chart collision.
    semantic_owners = defaultdict(list)
    for row in roster:
        semantic_owners[get_fact_key(row["song_title"], row["chart_difficulty"])].append(row)
    for semantic, owners in semantic_owners.items():
        types = sorted({r["exam_type"] for r in owners})
        if len(types) > 1 and not any(e.get("exception_type") == "CROSS_EXAM_DUPLICATE" and set(e.get("affected_slots", "").split(" | ")) == {r["slot_id"] for r in owners} for e in exceptions):
            for row in owners:
                row["conflict_status"] = "UNRESOLVED_CROSS_TYPE"
                row["conflict_with"] = " | ".join(types)
            exceptions.append({"exception_type": "SEMANTIC_CROSS_EXAM_DUPLICATE", "status": "UNRESOLVED",
                               "chart_key": f"{semantic[0]}#{semantic[1]}", "exam_types": " | ".join(types),
                               "affected_slots": " | ".join(r["slot_id"] for r in owners),
                               "detail": "Normalized title/difficulty indicate the same chart despite different source-key spelling."})

    for row in roster:
        if row["exam_type"] == "B-DCT Standard" and row["grade_no"] in {"1", "2", "3"}:
            exceptions.append({"exception_type": "STANDARD_1_3_HISTORIC_ASSIGNMENT_UNCONFIRMED", "status": "PROPOSED",
                               "chart_key": row["chart_key"], "exam_types": row["exam_type"], "affected_slots": row["slot_id"],
                               "detail": "Song/chart was preserved from current calculator heuristic; original official/historic slot chart evidence is not in the repository."})
    for row in roster:
        if row["exam_type"] == "B-DCT Standard" and 4 <= int(row["grade_no"]) <= 7:
            target = standard_proposal[(int(row["grade_no"]), int(row["slot_position"]))]["target_level_for_position"]
            actual_n, target_n = level_num(row["display_level"]), level_num(target)
            if actual_n is not None and target_n is not None and actual_n < target_n:
                exceptions.append({"exception_type": "STANDARD_4_7_BELOW_TARGET", "status": "PROPOSED_REQUIRES_APPROVAL",
                                   "chart_key": row["chart_key"], "exam_types": row["exam_type"], "affected_slots": row["slot_id"],
                                   "detail": f"Proposed level {row['display_level']} is one nominal step below unchanged target {target}; keep as proposal until user approves target-fit tradeoff."})
    if any(r["source_discrepancy_status"] != "NONE_RECORDED" for r in roster):
        for row in roster:
            if row["source_discrepancy_status"] != "NONE_RECORDED":
                exceptions.append({"exception_type": "SOURCE_LEVEL_DISAGREEMENT", "status": "UNRESOLVED",
                                   "chart_key": row["chart_key"], "exam_types": row["exam_type"], "affected_slots": row["slot_id"],
                                   "detail": "Audited Fandom snapshot reports Re:Boost CHAOS 11+; seore.org reports 11. Preserve the selected catalog value and do not use it as verified fact."})
    exceptions.append({"exception_type": "SV_STT_PURPOSE_FIT", "status": "PROPOSED_REQUIRES_PLAYTEST",
                       "chart_key": "", "exam_types": "B-DCT SV | B-DCT STT",
                       "affected_slots": " | ".join(r["slot_id"] for r in roster if r["exam_type"] in {"B-DCT SV", "B-DCT STT"}),
                       "detail": "SV candidates are separated from other exam types, but score stability is not established. STT candidates are separated, but TP/M.PERFECT precision suitability is not established. Neither selection is based solely on level distance."})
    exceptions.append({"exception_type": "DCT_MSTT_FORMULA", "status": "DEFERRED",
                       "chart_key": "", "exam_types": "DCT MSTT", "affected_slots": "all 60 MSTT slots",
                       "detail": "Roster candidates only; no formula or pass threshold was adopted."})
    exceptions.append({"exception_type": "OFFICIAL_SONG_IDS", "status": "PENDING_SOURCE",
                       "chart_key": "", "exam_types": "all", "affected_slots": "all slots with blank song_id",
                       "detail": "Official game song IDs are not evidenced by audit sources. No IDs were invented; source_song_key is a non-official citation key."})
    # Old archive comparisons are source-age notices, not changes to current listed levels.
    historical_mismatch_slots = [r for r in roster if r.get("historical_snapshot_match") == "NOTE_COUNT_MATCH_LEVEL_DIFF"]
    if historical_mismatch_slots:
        exceptions.append({"exception_type": "HISTORICAL_SNAPSHOT_LEVEL_DIFFERENCE", "status": "SOURCE_AGE_NOTE",
                           "chart_key": "", "exam_types": " | ".join(sorted({r["exam_type"] for r in historical_mismatch_slots})),
                           "affected_slots": " | ".join(r["slot_id"] for r in historical_mismatch_slots),
                           "detail": "The 2021 archived analysis matched title/difficulty and note count but its numeric level differed from the current audit source; retain current source display value and exclude old level from verification."})

    roster.sort(key=lambda r: (["B-DCT Standard", "B-DCT SV", "B-DCT STT", "DCT Standard", "DCT MSTT"].index(r["exam_type"]), int(r["grade_no"]), int(r["slot_position"])))
    write(OUTPUT, roster)
    write(EXCEPTIONS, exceptions)

    status_counts = Counter(r["conflict_status"] for r in roster)
    per_exam = Counter(r["exam_type"] for r in roster)
    report = [
        "# CYTUS II 통합 단위인정시험 — 288슬롯 편성 제안",
        "",
        "기준: `audit/288-slot-chart-validation`의 `b8c07e4`. 이 문서는 기존 1~4차 감사 자료로 작성한 첫 전체 편성 제안이며, 추가 감사 차수는 만들지 않았습니다.",
        "",
        "## 제안 범위",
        "",
        "| 시험 | 등급 | 제안 슬롯 | 상태 |",
        "|---|---:|---:|---|",
    ]
    counts = {"B-DCT Standard": 15, "B-DCT SV": 13, "B-DCT STT": 14, "DCT Standard": 15, "DCT MSTT": 15}
    for exam in ("B-DCT Standard", "B-DCT SV", "B-DCT STT", "DCT Standard", "DCT MSTT"):
        report.append(f"| {exam} | {counts[exam]} | {per_exam[exam]} | `PROPOSED` |")
    report += [
        "| **합계** | **72** | **288** | `PROPOSED` |",
        "",
        "모든 편성 행은 `PROPOSED`이며 `PLAYTESTED`/`VERIFIED`는 없습니다. DCT 공식 게임 곡 ID가 근거에서 확인되지 않아 `song_id`는 비워 두고, 출처 페이지 추적용 비공식 키를 따로 기록했습니다. 특수 레벨 표기는 출처 문자열 그대로 보존했습니다.",
        "",
        "## 편성 기준",
        "",
        "- B-DCT Standard 1~3단은 현재 계산기 곡·채보 추정을 그대로 제안하고 실제 과거 편성 확인은 예외로 기록했습니다.",
        "- Standard 4~7단은 감사 후보 16개를 제안 순서에 적용했습니다. 13개가 승인된 목표보다 표기 레벨 한 단계 낮으며 목표값은 바꾸지 않았습니다.",
        "- Standard 8~15단은 감사 당시 슬롯 후보를 유지했습니다. 같은 시험 안에서 반복되는 동일 채보는 예외 목록에 노출했습니다.",
        "- SV와 STT는 출처 확인 차트로 분리했습니다. Standard의 명시적 유지/후보 우선순위를 보존하고, 기존 SV는 가능하면 유지하며 STT는 교차 유형 충돌을 해소하도록 대안을 제시했습니다. 충돌 대안은 레벨과 보관된 구조 요약을 함께 고려했지만 점수 안정성과 TP 적합성은 검증되지 않았습니다.",
        "- DCT Standard와 DCT MSTT는 3차 감사의 별도 60곡 후보 목록을 유지했습니다. MSTT 산식과 합격 기준은 적용하지 않았습니다.",
        "- 같은 곡의 다른 채보는 허용했습니다. 동일 곡·동일 채보의 시험 유형 간 중복은 0건을 목표로 배정하고, 남은 경우 예외 목록에 기록했습니다.",
        "",
        "## 중복 및 미해결 예외",
        "",
        f"현재 교차 유형 중복은 {sum(1 for e in exceptions if e['exception_type'] in {'CROSS_EXAM_DUPLICATE', 'SEMANTIC_CROSS_EXAM_DUPLICATE'})}개 채보 키, {status_counts.get('UNRESOLVED_CROSS_TYPE', 0)}개 슬롯입니다. 같은 시험 유형 내부의 반복 차트는 {sum(1 for e in exceptions if e['exception_type']=='INTRA_EXAM_REPEAT')}개 차트 키로 예외 목록에 있습니다.",
        "",
        "[전체 288슬롯 CSV](roster_proposal_288.csv)에는 곡명, 채보, 표기 레벨, 근거, 출처, 충돌 상태, 검증 상태가 있습니다. [예외 CSV](roster_proposal_exceptions.csv)는 Standard 4~7 하향 후보, Standard 1~3 과거 편성 근거, 내부 중복, 목적 적합성, 출처 불일치와 MSTT 보류를 모읍니다.",
        "",
        "Re:Boost CHAOS는 감사된 Fandom 자료의 `11+`와 다른 커뮤니티 자료의 `11`이 불일치합니다. 해당 채보가 제안표에 있으면 선택값은 현재 감사 데이터 표기를 보존하고 예외로 표시합니다. 어느 값도 확정값으로 선언하지 않았습니다.",
        "",
        "## 승인 전 경계",
        "",
        "288개 모두 출처 기반 `PROPOSED`입니다. `CANDIDATE_REVIEWED`, `PLAYTESTED`, `VERIFIED`로 승격하지 않았습니다. 사용자가 별도 승인하기 전까지 `main`, 계산기 코드, GitHub Pages는 변경하지 않습니다.",
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Roster proposal: {len(roster)} slots; exceptions={len(exceptions)}; cross-type conflicts={status_counts.get('UNRESOLVED_CROSS_TYPE', 0)}; intra-exam repeated chart rows={status_counts.get('INTRA_EXAM_REPEAT', 0)}")


if __name__ == "__main__":
    main()
