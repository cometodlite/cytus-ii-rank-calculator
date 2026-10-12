#!/usr/bin/env python3
"""Refine the existing 288-slot proposal using only previously audited chart facts."""
import csv
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
INPUT = AUDIT / "roster_proposal_288.csv"
OUTPUT = AUDIT / "final_roster_candidates_288.csv"
EXCEPTIONS = AUDIT / "final_roster_exceptions.csv"
REPORT = AUDIT / "final_roster_summary.md"


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def norm(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return "".join(c for c in value if c.isalnum())


def key(title, difficulty):
    return norm(title), (difficulty or "").strip().upper()


def level_num(value):
    value = (value or "").strip()
    if value and value[0].isdigit():
        return int(value.rstrip("+")) + (0.5 if value.endswith("+") else 0)
    return None


def main():
    rows = read(INPUT)
    facts = read(AUDIT / "bdct_song_chart_facts.csv")
    source = {key(r["song_title"], r["chart_difficulty"]): r for r in facts}
    by_chart = {r["chart_key"]: r for r in facts}
    slots = {r["slot_id"]: r for r in read(AUDIT / "chart_slots.csv")}
    desk = {r["candidate_chart_key"]: r for r in read(AUDIT / "chart_desk_review.csv")}
    candidates = {
        # Standard Showcase duplicates: use five distinct, source-confirmed alternatives
        # chosen near the existing grade target; pattern suitability remains pending.
        "B-DCT-Standard-08-4": ("One Way Love", "GLITCH", "중복된 Showcase CHAOS를 분리. 목표 11에 가까운 출처 확인 레벨 12를 제안; 패턴 적합성 미검증."),
        "B-DCT-Standard-10-4": ("Bullet Waiting for Me (James Landino remix)", "GLITCH", "중복된 Showcase CHAOS를 분리. 목표 12에 가까운 출처 확인 레벨 13을 제안; 패턴 적합성 미검증."),
        "B-DCT-Standard-12-2": ("Grimoire of Crimson", "GLITCH", "중복된 Showcase CHAOS를 분리. 목표 12에 가까운 출처 확인 레벨 13을 제안; 패턴 적합성 미검증."),
        "B-DCT-Standard-13-4": ("The Spark", "GLITCH", "중복된 Showcase CHAOS를 분리. 목표 13+에 가까운 출처 확인 레벨 14를 제안; 패턴 적합성 미검증."),
        "B-DCT-Standard-15-3": ("Pure Powerstomper", "GLITCH", "중복된 Showcase CHAOS를 분리. 목표 14에 가까운 출처 확인 레벨 14를 제안; 패턴 적합성 미검증."),
        # These same-song alternatives are present in the audited source data and are not
        # assigned to another exam type in the current proposal.
        "B-DCT-Standard-08-2": ("Better than your error system", "HARD", "DCT MSTT와 겹친 Midnight CHAOS를 분리. 같은 곡 HARD 레벨 8 대안; 목표 10 대비 난이도 검토 필요."),
        "B-DCT-Standard-08-3": ("Purge", "CRASH", "DCT Standard와 겹친 Purge CHAOS를 분리. 같은 곡 CRASH α를 원문 표기대로 보존; 실제 난이도와 편성 적합성 확인 필요."),
        # Low-target repeated slots: alternatives reduce an exact-chart repeat and are
        # closer to the audited target level; this is a desk candidate, not playtest evidence.
        "B-DCT-SV-01-4": ("Better than your error system", "EASY", "SV 내부 Re:Boost CHAOS 반복을 분리. 출처 레벨 2가 감사 목표 6에 기존 11+보다 가깝지만 SV 점수 안정성 미검증."),
        "B-DCT-STT-01-2": ("Bullet Waiting for Me (James Landino remix)", "EASY", "STT 내부 Bullet Waiting for Me CHAOS 반복을 분리. 출처 레벨 1이 감사 목표 5에 기존 11+보다 가깝지만 TP 적합성 미검증."),
        "B-DCT-STT-05-2": ("Deadly Slot Game", "EASY", "STT 내부 Deadly Slot Game GLITCH 반복을 분리. 출처 레벨 3이 감사 목표 7에 기존 14+보다 가깝지만 TP 적합성 미검증."),
    }
    used_replacements = set()
    for row in rows:
        row["change_status"] = "UNCHANGED_FROM_22BC0DB"
        row["replaces_chart_key"] = ""
        row["difficulty_review_status"] = "NOT_APPLICABLE"
        if row["exam_type"] == "B-DCT Standard" and 4 <= int(row["grade_no"]) <= 7:
            row["difficulty_review_status"] = "REQUIRED_BEFORE_APPROVAL"
        if row["slot_id"] not in candidates:
            continue
        title, diff, rationale = candidates[row["slot_id"]]
        f = source[key(title, diff)]
        new_key = key(title, diff)
        if new_key in used_replacements:
            raise ValueError(f"replacement key assigned twice: {new_key}")
        used_replacements.add(new_key)
        old_key = row["chart_key"]
        row["replaces_chart_key"] = old_key
        row.update({
            "song_id": "", "source_song_key": f["source_song_key"], "song_title": f["song_title"],
            "chart_difficulty": f["chart_difficulty"], "display_level": f["actual_level"],
            "unlock_condition": f["unlock_condition"], "note_count": f["note_count"],
            "bpm": f["bpm"], "length": f["length"], "notes_per_min_proxy": f["notes_per_min"],
            "chart_key": f["chart_key"], "source_url": f["source_url"],
            "source_checked_on": f["source_checked_on"], "source_confidence": f["source_confidence"],
            "source_fact_status": f["fact_status"],
            "historical_snapshot_match": desk.get(f["chart_key"], {}).get("snapshot_match_status", "NO_ARCHIVE_RECORD"),
            "selection_basis": row["selection_basis"] + " 대체 후보: " + rationale,
            "source_discrepancy_status": "NONE_RECORDED",
            "change_status": "PROPOSED_REPLACEMENT",
            "difficulty_review_status": "REQUIRED_BEFORE_APPROVAL",
        })

    # Recalculate conflict flags from normalized song+chart identity.
    for row in rows:
        row["conflict_status"] = "NONE_CROSS_TYPE"
        row["conflict_with"] = ""
        row["roster_status"] = "PROPOSED"
        row["playtest_status"] = "PENDING"
        row["slot_verification_status"] = "PENDING"
    owners = defaultdict(list)
    for row in rows:
        owners[key(row["song_title"], row["chart_difficulty"])].append(row)
    exceptions = []
    for chart_key, group in owners.items():
        exams = sorted({r["exam_type"] for r in group})
        if len(exams) > 1:
            for row in group:
                row["conflict_status"] = "UNRESOLVED_CROSS_TYPE"
                row["conflict_with"] = " | ".join(exams)
            exceptions.append({"exception_type": "CROSS_EXAM_DUPLICATE", "status": "UNRESOLVED",
                               "chart_key": f"{chart_key[0]}#{chart_key[1]}", "exam_types": " | ".join(exams),
                               "affected_slots": " | ".join(r["slot_id"] for r in group),
                               "detail": "기존 출처 자료에서 목표 레벨과 교차 유형 독립성을 함께 만족하는 추가 대체 채보를 확보하지 못했습니다. Standard 1~3 및 4~7 고정 후보는 유지했습니다."})
            within_exam = defaultdict(list)
            for row in group:
                within_exam[row["exam_type"]].append(row)
            for exam, exam_rows in within_exam.items():
                if len(exam_rows) > 1:
                    exceptions.append({"exception_type": "INTRA_EXAM_REPEAT_WITH_CROSS_TYPE_CONFLICT", "status": "UNRESOLVED",
                                       "chart_key": f"{chart_key[0]}#{chart_key[1]}", "exam_types": exam,
                                       "affected_slots": " | ".join(r["slot_id"] for r in exam_rows),
                                       "detail": f"이 교차 유형 중복 키는 {exam} 안에서도 {len(exam_rows)}회 반복됩니다. 별도 출처 대안이 없어 예외로 유지했습니다."})
        elif len(group) > 1:
            for row in group:
                row["conflict_status"] = "INTRA_EXAM_REPEAT"
            exceptions.append({"exception_type": "INTRA_EXAM_REPEAT", "status": "REMAINS_AFTER_CANDIDATE_REVIEW",
                               "chart_key": f"{chart_key[0]}#{chart_key[1]}", "exam_types": exams[0],
                               "affected_slots": " | ".join(r["slot_id"] for r in group),
                               "detail": f"동일 시험 내 {len(group)}회 배정. 적용 가능한 대체 후보가 다른 시험에서 사용 중이거나 레벨 적합성이 낮아 추가 교체는 보류."})

    for row in rows:
        if row["exam_type"] == "B-DCT Standard" and 4 <= int(row["grade_no"]) <= 7:
            src = slots[row["slot_id"]]
            target = src.get("target_level", "")
            actual = level_num(row["display_level"])
            tgt = level_num(target)
            if actual is not None and tgt is not None and actual < tgt:
                exceptions.append({"exception_type": "STANDARD_4_7_BELOW_TARGET_AND_PLAYTEST_REQUIRED", "status": "PROPOSED_REQUIRES_PLAYTEST",
                                   "chart_key": row["chart_key"], "exam_types": row["exam_type"], "affected_slots": row["slot_id"],
                                   "detail": f"후보 레벨 {row['display_level']}은 기존 목표 {target}보다 낮습니다. 4~7단 16개 후보는 유지했고 실제 플레이 난이도 검증이 필요합니다."})
    for row in rows:
        if row["source_discrepancy_status"] != "NONE_RECORDED":
            exceptions.append({"exception_type": "SOURCE_LEVEL_DISAGREEMENT", "status": "UNRESOLVED",
                               "chart_key": row["chart_key"], "exam_types": row["exam_type"], "affected_slots": row["slot_id"],
                               "detail": "기존 감사의 Re:Boost CHAOS 표기 불일치가 남아 있습니다."})
    exceptions += [
        {"exception_type": "SV_PURPOSE_FIT", "status": "REQUIRES_PLAYTEST", "chart_key": "", "exam_types": "B-DCT SV",
         "affected_slots": " | ".join(r["slot_id"] for r in rows if r["exam_type"] == "B-DCT SV"),
         "detail": "SV 점수 안정성 및 실제 채점 재현성은 플레이 검증 전입니다."},
        {"exception_type": "STT_PURPOSE_FIT", "status": "REQUIRES_PLAYTEST", "chart_key": "", "exam_types": "B-DCT STT",
         "affected_slots": " | ".join(r["slot_id"] for r in rows if r["exam_type"] == "B-DCT STT"),
         "detail": "STT의 TP/M.PERFECT 정확도 적합성은 플레이 검증 전입니다."},
        {"exception_type": "DCT_TRACK_INDEPENDENCE_AND_MSTT_FORMULA", "status": "PRESERVED_DEFERRED", "chart_key": "", "exam_types": "DCT Standard | DCT MSTT",
         "affected_slots": " | ".join(r["slot_id"] for r in rows if r["exam_type"].startswith("DCT ")),
         "detail": "DCT Standard와 MSTT는 각각 기존 별도 60슬롯 후보 목록을 유지했습니다. MSTT 산식과 합격 기준은 확정하지 않았습니다."},
    ]
    for row in rows:
        if row["exam_type"] == "B-DCT Standard" and int(row["grade_no"]) <= 3:
            exceptions.append({"exception_type": "STANDARD_1_3_PRESERVED_HISTORIC_MAPPING_UNCONFIRMED", "status": "PROPOSED",
                               "chart_key": row["chart_key"], "exam_types": row["exam_type"], "affected_slots": row["slot_id"],
                               "detail": "사용자 지시에 따라 1~3단 기존 제안 채보를 유지했습니다. 과거 공식 편성표 근거는 미확인입니다."})

    rows.sort(key=lambda r: (["B-DCT Standard", "B-DCT SV", "B-DCT STT", "DCT Standard", "DCT MSTT"].index(r["exam_type"]), int(r["grade_no"]), int(r["slot_position"])))
    write(OUTPUT, rows)
    write(EXCEPTIONS, exceptions)
    cross_keys = sum(e["exception_type"] == "CROSS_EXAM_DUPLICATE" for e in exceptions)
    cross_slots = sum(len(e["affected_slots"].split(" | ")) for e in exceptions if e["exception_type"] == "CROSS_EXAM_DUPLICATE")
    repeat_exception_types = {"INTRA_EXAM_REPEAT", "INTRA_EXAM_REPEAT_WITH_CROSS_TYPE_CONFLICT"}
    repeat_keys = sum(e["exception_type"] in repeat_exception_types for e in exceptions)
    repeat_slots = sum(len(e["affected_slots"].split(" | ")) for e in exceptions if e["exception_type"] in repeat_exception_types)
    report = [
        "# CYTUS II 통합 단위인정시험 — 최종 편성 후보",
        "",
        "기준: 커밋 `22bc0db`의 `audit/roster_proposal_288.csv`. 별도 감사 차수 없이 기존 감사의 출처 확인 후보만 사용했습니다.",
        "",
        "| 시험 | 등급 | 슬롯 | 상태 |",
        "|---|---:|---:|---|",
        "| B-DCT Standard | 15 | 60 | PROPOSED |",
        "| B-DCT SV | 13 | 52 | PROPOSED |",
        "| B-DCT STT | 14 | 56 | PROPOSED |",
        "| DCT Standard | 15 | 60 | PROPOSED |",
        "| DCT MSTT | 15 | 60 | PROPOSED |",
        "| **합계** | **72** | **288** | **PROPOSED** |",
        "",
        f"기존 제안에서 출처 확인 대체 후보 10개를 적용했습니다. 전체 교차 유형 중복은 {cross_keys}개 키/{cross_slots}개 슬롯으로 감소했고, 시험 내부 반복은 {repeat_keys}개 키/{repeat_slots}개 슬롯에 남았습니다. 적용한 모든 대체안도 실전 적합성 확정이 아닌 `PROPOSED`입니다.",
        "",
        "Standard 4~7단 16개 후보와 기존 목표 레벨은 그대로 유지했습니다. 각 해당 슬롯에는 실제 난이도 확인 필요 플래그를 넣었습니다. DCT Standard와 MSTT는 각각 기존 60개 후보를 유지했고, MSTT 산식·합격 기준은 정하지 않았습니다.",
        "",
        "[최종 후보 288슬롯 CSV](final_roster_candidates_288.csv)에는 곡명, 채보, 레벨, 출처, 선정 사유, 변경 이력, 충돌과 난이도 검토 상태가 있습니다. [예외 CSV](final_roster_exceptions.csv)에는 남은 중복, 출처 불일치, 플레이 검증 필요 항목이 있습니다.",
        "",
        "모든 슬롯의 `roster_status`는 `PROPOSED`, `playtest_status`와 `slot_verification_status`는 `PENDING`입니다. 계산기 코드, `main`, GitHub Pages는 변경하지 않았습니다.",
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Final roster candidates: {len(rows)} slots; replacements={len(used_replacements)}; cross-type duplicate keys={cross_keys} ({cross_slots} slots); intra-exam repeat keys={repeat_keys} ({repeat_slots} rows); exceptions={len(exceptions)}")

if __name__ == "__main__":
    main()
