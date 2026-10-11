#!/usr/bin/env python3
"""Validate audit data without changing the public calculator or approving proposals."""

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
SLOT_FILE = AUDIT / "chart_slots.csv"
DCT_FILE = AUDIT / "dct_candidate_rosters.csv"
OVERLAP_FILE = AUDIT / "bdct_overlap_report.csv"
REPLACEMENT_FILE = AUDIT / "bdct_duplicate_replacement_candidates.csv"
COMPARISON_FILE = AUDIT / "bdct_standard_4_7_comparison.csv"
FACT_FILE = AUDIT / "bdct_song_chart_facts.csv"

EXPECTED = {
    "B-DCT Standard": (15, 60),
    "B-DCT SV": (13, 52),
    "B-DCT STT": (14, 56),
    "DCT Standard": (15, 60),
    "DCT MSTT": (15, 60),
}
LEVEL = re.compile(r"(?:[1-9]|1[0-6])\+?|[αβγ]")
SLOT_REQUIRED = {
    "slot_id", "exam_type", "grade_no", "grade_label", "slot_position",
    "target_level", "song_id", "catalog_song_key", "song_title",
    "current_chart_difficulty_assumption", "chart_difficulty", "chart_variant",
    "game_version", "actual_level", "unlock_condition", "source_url",
    "verified_on", "verification_status", "slot_assignment_evidence",
    "candidate_review_status", "playtest_status", "slot_verification_status",
}
VERIFIED_FIELDS = (
    "song_id", "song_title", "chart_difficulty", "chart_variant", "game_version",
    "actual_level", "unlock_condition", "source_url", "verified_on",
    "slot_assignment_evidence",
)
DCT_REQUIRED = {
    "slot_id", "exam_type", "grade_no", "slot_position", "target_level",
    "proposed_source_song_key", "official_song_id", "candidate_chart_key",
    "song_title", "chart_difficulty", "actual_level", "unlock_condition",
    "source_url", "candidate_status", "slot_assignment_status",
    "source_confidence", "source_snapshot_version", "source_checked_on",
}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), set(reader.fieldnames or [])


def valid_url(value):
    parsed = urlparse((value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def valid_date(value):
    try:
        date.fromisoformat((value or "").strip())
        return True
    except ValueError:
        return False


def level_num(value):
    value = (value or "").strip()
    if not value or not value[0].isdigit():
        return None
    return int(value.rstrip("+")) + (0.5 if value.endswith("+") else 0)


def main():
    errors = []
    slots, slot_fields = read_csv(SLOT_FILE)
    if SLOT_REQUIRED - slot_fields:
        errors.append(f"chart_slots.csv missing columns: {', '.join(sorted(SLOT_REQUIRED - slot_fields))}")
    slot_counts = Counter(r["exam_type"] for r in slots)
    if len(slots) != 288:
        errors.append(f"Expected 288 audit slots, found {len(slots)}")
    if len({r["slot_id"] for r in slots}) != len(slots):
        errors.append("chart_slots.csv slot_id values must be unique")
    if slot_counts != Counter({name: count for name, (_, count) in EXPECTED.items()}):
        errors.append(f"Unexpected exam slot counts: {dict(slot_counts)}")
    for exam, (grade_total, _) in EXPECTED.items():
        rows = [r for r in slots if r.get("exam_type") == exam]
        grade_counts = Counter(r.get("grade_no", "") for r in rows)
        if grade_counts != Counter({str(n): 4 for n in range(1, grade_total + 1)}):
            errors.append(f"{exam}: every grade must contain exactly four slots")
        positions = defaultdict(list)
        for row in rows:
            positions[row.get("grade_no", "")].append(row.get("slot_position", ""))
        if any(Counter(values) != Counter({"1": 1, "2": 1, "3": 1, "4": 1})
               for values in positions.values()):
            errors.append(f"{exam}: each grade must have slot positions 1 through 4 exactly once")

    statuses = Counter()
    verified_chart_keys = defaultdict(list)
    for row in slots:
        status = row.get("verification_status", "").strip().upper()
        statuses[status] += 1
        if status not in {"PENDING", "VERIFIED", "NEEDS_REVIEW", "REJECTED"}:
            errors.append(f"{row['slot_id']}: unsupported verification_status {status!r}")
        if status == "VERIFIED":
            missing = [f for f in VERIFIED_FIELDS if not row.get(f, "").strip()]
            if missing:
                errors.append(f"{row['slot_id']}: VERIFIED missing {', '.join(missing)}")
            if not LEVEL.fullmatch(row.get("actual_level", "").strip()):
                errors.append(f"{row['slot_id']}: unsupported actual_level {row.get('actual_level')!r}")
            if not valid_date(row.get("verified_on")):
                errors.append(f"{row['slot_id']}: verified_on must be YYYY-MM-DD")
            if not valid_url(row.get("source_url")):
                errors.append(f"{row['slot_id']}: source_url must be an absolute HTTP(S) URL")
            key = tuple(row.get(k, "").strip() for k in
                        ("song_id", "chart_difficulty", "chart_variant", "game_version"))
            verified_chart_keys[key].append(row)
        # A fact check cannot silently promote an assignment to verified.
        if row.get("candidate_chart_fact_status", "").upper() == "SOURCE_CONFIRMED" and status == "VERIFIED":
            if not row.get("slot_assignment_evidence", "").strip():
                errors.append(f"{row['slot_id']}: chart fact alone cannot verify a slot assignment")
        if row.get("exam_type", "").startswith("B-DCT") and row.get("candidate_chart_fact_status") != "SOURCE_CONFIRMED":
            errors.append(f"{row['slot_id']}: B-DCT candidate chart fact is missing")
        if row.get("candidate_review_status") != "PENDING" or row.get("playtest_status") != "PENDING" or \
                row.get("slot_verification_status") != "PENDING":
            errors.append(f"{row['slot_id']}: review, playtest, and slot verification must remain PENDING")

    for key, owners in verified_chart_keys.items():
        if len({r["exam_type"] for r in owners}) > 1:
            errors.append(f"Cross-exam verified chart duplicate {key}: " + ", ".join(r["slot_id"] for r in owners))

    # This report is conditional on the app's difficulty heuristic, not proof of actual assignments.
    overlaps, overlap_fields = read_csv(OVERLAP_FILE)
    if len(overlaps) != 37:
        errors.append(f"Expected 37 potential overlap keys, found {len(overlaps)}")
    if any(r.get("overlap_status") != "POTENTIAL_FROM_APP_DIFFICULTY_HEURISTIC" or
           r.get("slot_assignment_status") != "PENDING" for r in overlaps):
        errors.append("Overlap rows must remain heuristic-only and PENDING")
    overlap_exam_counts = Counter(r.get("exam_type_count", "") for r in overlaps)
    if overlap_exam_counts != Counter({"3": 35, "2": 2}):
        errors.append(f"Unexpected overlap distribution: {dict(overlap_exam_counts)}")

    dct_rows, dct_fields = read_csv(DCT_FILE)
    if DCT_REQUIRED - dct_fields:
        errors.append(f"dct_candidate_rosters.csv missing columns: {', '.join(sorted(DCT_REQUIRED - dct_fields))}")
    if len(dct_rows) != 120:
        errors.append(f"Expected 120 DCT candidates, found {len(dct_rows)}")
    dct_keys = defaultdict(list)
    dct_songs = defaultdict(list)
    for exam in ("DCT Standard", "DCT MSTT"):
        rows = [r for r in dct_rows if r.get("exam_type") == exam]
        if len(rows) != 60:
            errors.append(f"{exam}: expected 60 candidates, found {len(rows)}")
        grades = Counter(r.get("grade_no", "") for r in rows)
        if grades != Counter({str(n): 4 for n in range(1, 16)}):
            errors.append(f"{exam}: expected 15 grades with four candidates each")
        if any(r.get("slot_assignment_status") != "PENDING" for r in rows):
            errors.append(f"{exam}: proposal slot assignments must remain PENDING")
        if any(r.get("candidate_status") != "SOURCE_CONFIRMED" for r in rows):
            errors.append(f"{exam}: unexpected candidate_status")
        if any(r.get("candidate_review_status") != "PENDING" or r.get("playtest_status") != "PENDING"
               or r.get("slot_verification_status") != "PENDING" for r in rows):
            errors.append(f"{exam}: candidates must remain unreviewed, unplayed, and unassigned")
        if len({r.get("slot_id") for r in rows}) != len(rows):
            errors.append(f"{exam}: duplicate slot_id")
        for row in rows:
            label = f"{row.get('slot_id')}"
            if row.get("target_level", "").strip() != row.get("actual_level", "").strip():
                errors.append(f"{label}: candidate level does not match proposal target")
            if not LEVEL.fullmatch(row.get("actual_level", "").strip()):
                errors.append(f"{label}: unsupported actual_level {row.get('actual_level')!r}")
            if not row.get("proposed_source_song_key", "").strip() or not row.get("candidate_chart_key", "").strip():
                errors.append(f"{label}: candidate source/chart key missing")
            if not row.get("unlock_condition", "").strip():
                errors.append(f"{label}: unlock condition missing")
            if not valid_url(row.get("source_url")):
                errors.append(f"{label}: source_url must be absolute HTTP(S)")
            if not valid_date(row.get("source_checked_on")):
                errors.append(f"{label}: source_checked_on must be YYYY-MM-DD")
            dct_keys[row.get("candidate_chart_key", "")].append(row)
            dct_songs[row.get("proposed_source_song_key", "")].append(row)
    for key, owners in dct_keys.items():
        if len(owners) > 1:
            errors.append(f"DCT candidate chart reused: {key}")
    for key, owners in dct_songs.items():
        if len(owners) > 1:
            errors.append(f"DCT candidate song reused: {key}")
    for field, label in (("candidate_chart_key", "chart"), ("proposed_source_song_key", "song")):
        standard = {r.get(field, "") for r in dct_rows if r.get("exam_type") == "DCT Standard"}
        mstt = {r.get(field, "") for r in dct_rows if r.get("exam_type") == "DCT MSTT"}
        if standard & mstt:
            errors.append(f"DCT Standard and MSTT share candidate {label} keys: {sorted(standard & mstt)}")

    grade_label = {**{str(n): f"{n}단" for n in range(1, 12)},
                   "12": "자격 1", "13": "자격 2", "14": "자격 3", "15": "MASTER"}
    for filename, rows in (("dct_candidate_rosters.csv", dct_rows), ("chart_slots.csv", slots)):
        for row in rows:
            if row.get("exam_type") in {"DCT Standard", "DCT MSTT"} and \
                    row.get("grade_label") != grade_label.get(row.get("grade_no", "")):
                errors.append(f"{filename}: {row.get('slot_id')} grade_no/grade_label mismatch")

    replacements, _ = read_csv(REPLACEMENT_FILE)
    if any(r.get("candidate_status") != "SOURCE_CONFIRMED" for r in replacements):
        errors.append("Replacement candidates must retain source-fact status")
    if any(r.get("candidate_key_used_by_current_app_mapping") not in {"YES", "NO"} for r in replacements):
        errors.append("Replacement candidates must expose current heuristic conflict flag")

    comparisons, _ = read_csv(COMPARISON_FILE)
    if len(comparisons) != 16 or any(r.get("slot_assignment_status") != "PENDING" for r in comparisons):
        errors.append("Standard grades 4-7 comparison must contain 16 pending rows")

    facts, _ = read_csv(FACT_FILE)
    if len(facts) != 125:
        errors.append(f"Expected 125 B-DCT chart facts, found {len(facts)}")
    if any(r.get("fact_status") != "SOURCE_CONFIRMED" for r in facts):
        errors.append("Unexpected B-DCT chart fact status")
    if any(not valid_date(r.get("source_checked_on")) for r in facts):
        errors.append("B-DCT chart facts need a valid source_checked_on date")

    standard_review, _ = read_csv(AUDIT / "bdct_standard_4_7_recomposition_candidates.csv")
    if len(standard_review) != 16:
        errors.append(f"Expected 16 Standard 4-7 candidate rows, found {len(standard_review)}")
    if any(r.get("source_status") != "SOURCE_CONFIRMED" or
           r.get("candidate_review_status") != "PENDING" or r.get("playtest_status") != "PENDING" or
           r.get("slot_verification_status") != "PENDING" for r in standard_review):
        errors.append("Standard 4-7 candidates must remain source-confirmed and pending further review")
    for grade in range(4, 8):
        group = sorted((r for r in standard_review if int(r["grade_no"]) == grade),
                       key=lambda r: int(r["proposed_position"]))
        if len(group) != 4 or [int(r["proposed_position"]) for r in group] != [1, 2, 3, 4]:
            errors.append(f"Standard grade {grade}: proposed order must contain four positions")
        values = [level_num(r["proposed_level"]) for r in group]
        if any(v is None for v in values) or values != sorted(values):
            errors.append(f"Standard grade {grade}: proposed chart levels must be nondecreasing")

    overlap_review, _ = read_csv(AUDIT / "bdct_sv_stt_overlap_resolution.csv")
    alternatives, _ = read_csv(AUDIT / "bdct_cross_type_replacement_options.csv")
    dct_review, _ = read_csv(AUDIT / "dct_candidate_review.csv")
    playtests, _ = read_csv(AUDIT / "chart_playtest_queue.csv")
    progression, _ = read_csv(AUDIT / "grade_level_progression.csv")
    if len(overlap_review) != 37:
        errors.append(f"Expected 37 overlap resolution rows, found {len(overlap_review)}")
    if len(alternatives) != 291:
        errors.append(f"Expected 291 cross-type replacement options, found {len(alternatives)}")
    if len(dct_review) != 120:
        errors.append(f"Expected 120 DCT candidate review rows, found {len(dct_review)}")
    if len(playtests) != 237:
        errors.append(f"Expected 237 unique playtest queue charts, found {len(playtests)}")
    if playtests and ("priority_rank" not in playtests[0] or "priority_class" not in playtests[0]):
        errors.append("Playtest queue must include 4th-audit priority fields")
    elif sorted(int(r["priority_rank"]) for r in playtests) != list(range(1, 238)):
        errors.append("Playtest queue priority ranks must be unique and contiguous 1..237")
    desk_review, _ = read_csv(AUDIT / "chart_desk_review.csv")
    if len(desk_review) != 237:
        errors.append(f"Expected 237 desk-review rows, found {len(desk_review)}")
    if any(r.get("desk_review_status") not in {"DESK_REVIEWED", "PENDING"} or r.get("playtest_status") != "PENDING"
           for r in desk_review):
        errors.append("Desk review must be evidence-backed; playtest must remain PENDING")
    desk_by_key = {r.get("candidate_chart_key"): r for r in desk_review}
    if any(r.get("desk_review_status") != desk_by_key.get(r.get("candidate_chart_key"), {}).get("desk_review_status")
           for r in playtests):
        errors.append("Playtest queue desk-review states must match the chart analysis report")
    if any(r.get("desk_review_status") == "DESK_REVIEWED" and
           (not r.get("source_commit") or not r.get("snapshot_note_count") or not r.get("snapshot_top_rhythm_patterns"))
           for r in desk_review):
        errors.append("DESK_REVIEWED rows need traceable chart structure fields and source revision")
    if any(r.get("provisional_retain_type_by_level_fit") != "UNRESOLVED" for r in overlap_review):
        errors.append("SV/STT overlap ownership must remain UNRESOLVED")
    if len(progression) != 72:
        errors.append(f"Expected 72 grade progression rows, found {len(progression)}")
    lower, _ = read_csv(AUDIT / "standard_4_7_lower_level_rationale.csv")
    conflicts, _ = read_csv(AUDIT / "standard_4_7_duplicate_conflicts.csv")
    grade_ids, _ = read_csv(AUDIT / "dct_grade_identifier_consistency.csv")
    blockers, _ = read_csv(AUDIT / "audit_4_approval_blockers.csv")
    if len(lower) != 13 or any(r.get("review_status") != "PENDING" for r in lower):
        errors.append("Standard 4-7 lower-level rationale must document 13 pending rows")
    if len(conflicts) != 2 or any(not r.get("replacement_decision", "").startswith("UNRESOLVED") for r in conflicts):
        errors.append("Re:Boost and Green Hope duplicate candidates must remain unresolved")
    if len(grade_ids) != 30 or any(r.get("status") != "PASS" or int(r.get("slot_count", 0)) != 4 for r in grade_ids):
        errors.append("DCT grade identifier report must cover 30 normalized grades with four slots each")
    if len(blockers) != 7:
        errors.append("4th-audit approval blocker list must contain seven areas")
    for name, data in (("overlap resolutions", overlap_review), ("replacement options", alternatives),
                       ("DCT review", dct_review), ("playtest queue", playtests)):
        if any(r.get("source_status") != "SOURCE_CONFIRMED" or
               r.get("candidate_review_status") != "PENDING" or r.get("playtest_status") != "PENDING"
               or r.get("slot_verification_status") != "PENDING" for r in data):
            errors.append(f"{name}: source facts cannot be promoted to reviewed, playtested, or verified")
    if any(r.get("target_fit") != "EXACT" for r in dct_review):
        errors.append("DCT candidate review rows must retain exact source-level/target match flag")
    if any(r.get("candidate_review_status") != "PENDING" or r.get("playtest_status") != "PENDING"
           or r.get("slot_verification_status") != "PENDING" for r in progression):
        errors.append("Grade progression rows cannot promote candidates beyond PENDING review")

    print(f"Audit slots: {len(slots)} / 288; statuses: {dict(statuses)}")
    for exam, (grades, count) in EXPECTED.items():
        print(f"  {exam}: {slot_counts[exam]} slots, {grades} grades")
    print(f"B-DCT chart facts: {len(facts)}; DCT proposals: {len(dct_rows)}; potential overlaps: {len(overlaps)}")
    print(f"Replacement candidates: {len(replacements)}; heuristic conflicts: "
          f"{sum(r.get('candidate_key_used_by_current_app_mapping') == 'YES' for r in replacements)}")
    print(f"4th-audit: Standard 4-7={len(standard_review)}; overlap resolutions={len(overlap_review)}; "
          f"alternatives={len(alternatives)}; DCT review={len(dct_review)}; "
          f"grade progression={len(progression)}; playtest queue={len(playtests)}; "
          f"desk-reviewed={sum(r.get('desk_review_status') == 'DESK_REVIEWED' for r in desk_review)}; "
          f"pending desk review={sum(r.get('desk_review_status') == 'PENDING' for r in desk_review)}")
    if errors:
        print("Validation: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Validation: PASS (no slot assignments promoted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
