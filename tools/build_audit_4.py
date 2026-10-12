#!/usr/bin/env python3
"""Build fourth-pass review artifacts; never changes public calculator or assignments."""

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"


def read(name):
    with (AUDIT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows, fields=None):
    if fields is None:
        fields = list(rows[0]) if rows else []
    with (AUDIT / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def level_num(s):
    s = (s or "").strip()
    if not s or not s[0].isdigit():
        return None
    return int(s.rstrip("+")) + (0.5 if s.endswith("+") else 0)


def main():
    std = read("bdct_standard_4_7_recomposition_candidates.csv")
    facts = read("bdct_song_chart_facts.csv")
    historical_desk = read("chart_desk_review.csv") if (AUDIT / "chart_desk_review.csv").exists() else []
    desk_by_key = {r["candidate_chart_key"]: r for r in historical_desk}
    facts_by_song = defaultdict(list)
    for f in facts:
        facts_by_song[f["source_song_key"]].append(f)
    lower = []
    for r in std:
        if level_num(r["signed_level_delta"]) == -1 or r["signed_level_delta"] == "-1.0":
            song_key = r["proposed_chart_key"].rsplit("#", 1)[0]
            target = level_num(r["target_level_for_position"])
            matching = [f for f in facts_by_song[song_key] if level_num(f["actual_level"]) == target]
            lower.append({
                "grade_no": r["grade_no"], "grade_label": r["grade_label"],
                "proposed_position": r["proposed_position"], "slot_id": r["original_slot_id"],
                "song_title": r["proposed_song_title"], "chart_key": r["proposed_chart_key"],
                "chart_difficulty": r["proposed_chart_difficulty"], "source_level": r["proposed_level"],
                "target_level": r["target_level_for_position"], "level_delta": r["signed_level_delta"],
                "same_song_exact_target_chart_in_audited_facts": "YES" if matching else "NO",
                "reason_for_retaining_lower_candidate": "Closest source-listed same-song chart to the pre-set target among the audited chart facts; no exact-target same-song chart was present in this fact set. This is a catalog-availability rationale only, not proof of comparable or suitable practical difficulty.",
                "difficulty_evidence": "Nominal source level only; rhythm, hand placement, note density distribution, endurance, score stability and TP suitability not established.",
                "source_url": r["source_url"], "source_checked_on": r["source_checked_on"],
                "source_confidence": r["source_confidence"], "review_status": "PENDING",
                "slot_assignment_status": "PENDING", "playtest_status": "PENDING"
            })
    write("standard_4_7_lower_level_rationale.csv", lower)

    conflicts = []
    conflict_specs = [
        ("Re:Boost", "HARD", "B-DCT Standard grade 4 slot 1 (proposed); B-DCT SV grade 1 slot 4 (app-assumed); B-DCT STT grade 2 slot 2 (app-assumed)", "TARGET 6; candidate HARD level 5; same exact chart key appears across three types"),
        ("Green Hope", "HARD", "B-DCT Standard grade 4 slot 3 (proposed); B-DCT SV grade 2 slot 4 (app-assumed)", "TARGET 7; candidate HARD level 7; same exact chart key appears across two types"),
    ]
    for song, diff, owners, issue in conflict_specs:
        key = next((r["proposed_chart_key"].rsplit("#", 1)[0] for r in std if r["proposed_song_title"] == song), "")
        alternatives = [f'{f["chart_difficulty"]} {f["actual_level"]}' for f in facts_by_song.get(key, []) if f["chart_difficulty"] != diff]
        conflicts.append({"song_title": song, "conflict_chart_key": f"{key}#{diff}", "affected_types_and_slots": owners,
                          "issue": issue, "other_source_listed_charts": " | ".join(alternatives),
                          "replacement_decision": "UNRESOLVED: alternatives have different nominal levels and no pattern/play evidence establishes equivalence.",
                          "source_status": "SOURCE_CONFIRMED", "slot_assignment_status": "PENDING", "playtest_status": "PENDING"})
    write("standard_4_7_duplicate_conflicts.csv", conflicts)

    overlaps = read("bdct_sv_stt_overlap_resolution.csv")
    for r in overlaps:
        r["provisional_retain_type_by_level_fit"] = "UNRESOLVED"
        r["assumption_provenance"] = "index.html difficulty(i): B-DCT SV/STT use HARD at grade_no 1-2 and CHAOS thereafter. B-DCT Standard/basic uses HARD for grade 1 all slots, grade 2 positions 2-4, and grade 3 position 3; CHAOS otherwise. App code heuristic only, not evidence of historical official roster."
        r["overlap_evidence_status"] = "POTENTIAL_KEY_OVERLAP_FROM_APP_ASSUMPTION"
        r["score_stability_vs_tp_fit"] = "UNRESOLVED: no chart event / replay evidence; level distance is insufficient to choose ownership."
        r["sv_review_focus"] = "Inspect scoring robustness across non-perfect judgments, note-type mix, combo breaks and repeatability; no candidate-specific finding yet."
        r["stt_review_focus"] = "Inspect timing density, precision traps, hold/drag/flick judgment exposure and M.PERFECT repeatability; no candidate-specific finding yet."
        evidence = desk_by_key.get(r["candidate_chart_key"], {})
        r["historical_chart_analysis_status"] = evidence.get("desk_review_status", "PENDING")
        r["historical_snapshot_match"] = evidence.get("snapshot_match_status", "NO_ARCHIVE_RECORD")
        r["historical_note_type_counts"] = (" | ".join(f'{name}={evidence.get(col, "")}' for name, col in (
            ("Click", "snapshot_click_count"), ("Hold", "snapshot_hold_count"), ("Long", "snapshot_long_count"),
            ("DragH", "snapshot_dragh_count"), ("Drag", "snapshot_drag_count"), ("Flick", "snapshot_flick_count"),
            ("CDragH", "snapshot_cdragh_count"), ("CDrag", "snapshot_cdrag_count"))) if evidence.get("desk_review_status") == "DESK_REVIEWED" else "")
        r["historical_density_avg_max"] = (f'{evidence.get("snapshot_note_density_avg", "")} / {evidence.get("snapshot_note_density_max", "")}' if evidence.get("desk_review_status") == "DESK_REVIEWED" else "")
        r["historical_rhythm_density_avg_max"] = (f'{evidence.get("snapshot_rhythm_density_avg", "")} / {evidence.get("snapshot_rhythm_density_max", "")}' if evidence.get("desk_review_status") == "DESK_REVIEWED" else "")
        r["historical_top_rhythm_patterns"] = evidence.get("snapshot_top_rhythm_patterns", "") if evidence.get("desk_review_status") == "DESK_REVIEWED" else ""
        r["historical_analysis_source_commit"] = evidence.get("source_commit", "") if evidence.get("desk_review_status") == "DESK_REVIEWED" else ""
        r["notes"] = "Conditional 37-key overlap under app heuristic. Not a confirmed assigned-slot collision; retain-type choice remains UNRESOLVED pending chart-level evidence and user-approved allocation."
    write("bdct_sv_stt_overlap_resolution.csv", overlaps)

    dct = read("dct_candidate_rosters.csv")
    grade_map = {**{str(n): f"{n}단" for n in range(1, 12)}, "12": "자격 1", "13": "자격 2", "14": "자격 3", "15": "MASTER"}
    id_rows = []
    for exam in ("DCT Standard", "DCT MSTT"):
        for no, label in grade_map.items():
            rows = [r for r in dct if r["exam_type"] == exam and r["grade_no"] == no]
            id_rows.append({"exam_type": exam, "internal_grade_no": no, "display_grade_label": label,
                            "slot_count": len(rows), "candidate_labels_match_normalization": "YES" if rows and all(r["grade_label"] == label for r in rows) else "NO",
                            "normalization_rule": "Internal ordinal 1-11 => displayed N단; 12-14 => 자격 1-3; 15 => MASTER. grade_no remains numeric machine key and is not shown as a public grade name.",
                            "status": "PASS" if rows and all(r["grade_label"] == label for r in rows) else "FAIL"})
    write("dct_grade_identifier_consistency.csv", id_rows)

    # Derive a deterministic queue urgency from outstanding decisions, without implying review completion.
    queue = read("chart_playtest_queue.csv")
    overlap_keys = {r["candidate_chart_key"] for r in overlaps}
    standard_keys = {r["proposed_chart_key"] for r in std}
    dct_lookup = defaultdict(list)
    for r in dct:
        dct_lookup[r["candidate_chart_key"]].append(r)
    for r in queue:
        r.pop("desk_review_note", None)
        key = r["candidate_chart_key"]
        linked = dct_lookup.get(key, [])
        linked_grades = [int(x["grade_no"]) for x in linked]
        linked_exam = sorted({x["exam_type"] for x in linked})
        if key in overlap_keys or key in standard_keys:
            p, why = "P0", "Potential cross-type overlap or Standard 4-7 under-target/transition decision; resolve before roster approval."
        elif linked and (max(linked_grades) >= 14 or level_num(r["source_level"]) >= 16 or float(r["notes_per_min_proxy"] or 0) >= 700):
            p, why = "P1", "DCT grade 14-15, level 16+, or metadata-density outlier; review before broad progression review."
        elif not linked:
            p, why = "P2", "B-DCT candidate mapping or replacement needing purpose-specific review."
        else:
            p, why = "P3", "Remaining DCT candidate; review after critical overlap, transition and high-end cases."
        r["priority_class"] = p
        r["priority_reason"] = why
        r["linked_dct_grade_nos"] = "|".join(str(n) for n in linked_grades)
        r["linked_dct_exam_types"] = "|".join(linked_exam)
        desk = desk_by_key.get(key, {})
        r["desk_review_status"] = desk.get("desk_review_status", "PENDING")
        r["desk_review_snapshot_match"] = desk.get("snapshot_match_status", "NO_ARCHIVE_RECORD")
        r["desk_review_snapshot_date"] = desk.get("source_snapshot_date", "")
        r["desk_review_limitation"] = desk.get("review_scope_and_limit", "No archive analysis record was imported for this chart key.")
        r["playtest_status"] = "PENDING"
        r["playtest_required_fields"] = "device/game_version; player; attempts; score; TP; judgment counts; observed rhythm/hand/stamina issues; date"
    p_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    queue.sort(key=lambda r: (p_rank[r["priority_class"]], -(float(r["notes_per_min_proxy"]) if r["notes_per_min_proxy"] else 0), r["candidate_chart_key"]))
    for i, r in enumerate(queue, 1):
        r["priority_rank"] = i
    write("chart_playtest_queue.csv", queue)

    # A concise machine-readable list of decisions that block final approval.
    blockers = [
        ["B-DCT Standard 4-7", "13 candidates are one nominal level below the approved targets", "Review play results and chart structure; exact target chart absent in audited same-song fact set", "PENDING"],
        ["B-DCT Standard duplicates", "Re:Boost HARD overlaps SV and STT; Green Hope HARD overlaps SV under app heuristic", "Approve which type may retain each exact chart, or approve a sourced replacement; current alternatives are not equivalent by level alone", "UNRESOLVED"],
        ["B-DCT SV/STT overlaps", "37 potential chart keys, conditional on HARD/CHAOS app rule", "Inspect purpose-specific evidence and confirm whether source assignment is real", "UNRESOLVED"],
        ["Standard grades 1-3", "Current app-assumed source levels are non-monotonic and grade 4 proposal reconnects near grade 1 levels", "Recover/confirm actual historic chart assignments and intended target bands before judging continuity", "UNRESOLVED"],
        ["DCT Standard/MSTT", "120 independent candidates have catalog metadata; structural diversity not inspected", "Chart visual/event data and playtest records required; preserve independent lists", "PENDING"],
        ["MSTT", "Formula and pass threshold remain undefined", "Separate explicit approval required before any pass/fail calculation", "DEFERRED"],
        ["All 288 slots", "No candidate-to-slot assignment evidence is confirmed", "Keep every slot PENDING until user approves final allocation and supporting evidence is recorded", "PENDING"],
    ]
    write("audit_4_approval_blockers.csv", [dict(zip(["area", "finding", "required_to_resolve", "status"], row)) for row in blockers])

    write("audit_4_source_discrepancies.csv", [{
        "chart_key": "Re:Boost#CHAOS", "field": "actual_level", "audit_snapshot_value": "11+",
        "independently_checked_page_value": "11", "audit_snapshot_source": "https://cytus.fandom.com/wiki/Re:Boost",
        "independently_checked_source": "https://seore.org/w/Re:Boost", "checked_on": "2026-10-12",
        "source_quality": "Both are community-maintained; neither is official game data.",
        "disposition": "UNRESOLVED: retain source-specific raw values and recheck against in-game current version before relying on level. Do not normalize away the + marker."
    }])

    print(f"4th audit artifacts built: lower={len(lower)}, overlaps={len(overlaps)}, DCT identifiers={len(id_rows)}, queue={len(queue)}; desk-reviewed={sum(r.get('desk_review_status') == 'DESK_REVIEWED' for r in queue)}; pending desk review={sum(r.get('desk_review_status') == 'PENDING' for r in queue)}")


if __name__ == "__main__":
    main()
