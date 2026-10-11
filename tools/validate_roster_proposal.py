#!/usr/bin/env python3
"""Validate completeness and non-promotion safeguards for the 288-slot proposal."""
import csv
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
EXPECTED = {
    "B-DCT Standard": (15, 4),
    "B-DCT SV": (13, 4),
    "B-DCT STT": (14, 4),
    "DCT Standard": (15, 4),
    "DCT MSTT": (15, 4),
}

def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def norm(value):
    s = unicodedata.normalize("NFKC", value or "").casefold()
    return "".join(c for c in s if c.isalnum())

def main():
    rows = read(AUDIT / "roster_proposal_288.csv")
    exceptions = read(AUDIT / "roster_proposal_exceptions.csv")
    errors = []
    if len(rows) != 288:
        errors.append(f"expected 288 rows, found {len(rows)}")
    required = ("slot_id", "exam_type", "grade_no", "grade_label", "slot_position", "song_title",
                "chart_difficulty", "display_level", "selection_basis", "source_url", "source_checked_on",
                "conflict_status", "roster_status", "playtest_status", "slot_verification_status")
    for col in required:
        if any(not r.get(col, "").strip() for r in rows):
            errors.append(f"required column {col} has blank values")
    slot_ids = [r["slot_id"] for r in rows]
    if len(set(slot_ids)) != len(slot_ids):
        errors.append("duplicate slot_id")
    by_exam = defaultdict(list)
    for r in rows:
        by_exam[r["exam_type"]].append(r)
        if r["roster_status"] != "PROPOSED":
            errors.append(f"slot promoted from PROPOSED: {r['slot_id']}={r['roster_status']}")
        if r["playtest_status"] == "PLAYTESTED" or r["slot_verification_status"] == "VERIFIED":
            errors.append(f"unearned verification state: {r['slot_id']}")
    if set(by_exam) != set(EXPECTED):
        errors.append(f"exam set mismatch: {sorted(by_exam)}")
    for exam, (grade_count, slots_per_grade) in EXPECTED.items():
        group = by_exam[exam]
        if len(group) != grade_count * slots_per_grade:
            errors.append(f"{exam}: expected {grade_count * slots_per_grade}, found {len(group)}")
        grades = defaultdict(list)
        for r in group:
            grades[int(r["grade_no"])].append(r)
        if set(grades) != set(range(1, grade_count + 1)):
            errors.append(f"{exam}: grade numbers are not 1..{grade_count}")
        for grade, grade_rows in grades.items():
            if len(grade_rows) != slots_per_grade or sorted(int(r["slot_position"]) for r in grade_rows) != list(range(1, slots_per_grade + 1)):
                errors.append(f"{exam} grade {grade}: positions/count invalid")
    owners = defaultdict(list)
    for r in rows:
        owners[(norm(r["song_title"]), r["chart_difficulty"].strip().upper())].append(r)
    cross_keys = {k: v for k, v in owners.items() if len({r["exam_type"] for r in v}) > 1}
    exception_rows = [e for e in exceptions if e["exception_type"] in {"CROSS_EXAM_DUPLICATE", "SEMANTIC_CROSS_EXAM_DUPLICATE"}]
    exception_slots = {slot for e in exception_rows for slot in e["affected_slots"].split(" | ") if slot}
    if any(r["conflict_status"] != "UNRESOLVED_CROSS_TYPE" for group in cross_keys.values() for r in group):
        errors.append("cross-exam duplicate lacks UNRESOLVED_CROSS_TYPE status")
    if any(r["slot_id"] not in exception_slots for group in cross_keys.values() for r in group):
        errors.append("cross-exam duplicate missing from exception list")
    if any(r["conflict_status"] == "UNRESOLVED_CROSS_TYPE" for r in rows) and not exception_rows:
        errors.append("conflict status exists but exception list is empty")
    # Special level notation is retained verbatim from the source candidate table.
    facts = read(AUDIT / "bdct_song_chart_facts.csv")
    dct = read(AUDIT / "dct_candidate_rosters.csv")
    source_levels = {(norm(r["song_title"]), r["chart_difficulty"].upper()): r["actual_level"] for r in facts + dct}
    for r in rows:
        key = (norm(r["song_title"]), r["chart_difficulty"].upper())
        if key in source_levels and r["display_level"] != source_levels[key]:
            errors.append(f"source level changed for {r['slot_id']}: {r['display_level']} != {source_levels[key]}")
    if errors:
        print("Roster proposal validation: FAIL")
        for e in errors:
            print("-", e)
        return 1
    print(f"Roster proposal validation: PASS ({len(rows)} slots; {len(cross_keys)} cross-type duplicate keys / {sum(len(v) for v in cross_keys.values())} affected rows documented; all slots PROPOSED; no PLAYTESTED/VERIFIED promotion)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
