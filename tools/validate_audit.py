#!/usr/bin/env python3
"""Validate the 288-slot chart audit without changing the public calculator."""

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit" / "chart_slots.csv"
EXPECTED = {
    "B-DCT Standard": (15, 60),
    "B-DCT SV": (13, 52),
    "B-DCT STT": (14, 56),
    "DCT Standard": (15, 60),
    "DCT MSTT": (15, 60),
}
REQUIRED = {
    "slot_id", "exam_type", "grade_no", "grade_label", "slot_position",
    "target_level", "song_id", "catalog_song_key", "song_title",
    "current_chart_difficulty_assumption", "chart_difficulty", "chart_variant",
    "game_version", "actual_level", "unlock_condition", "source_url",
    "verified_on", "verification_status", "notes",
}
VERIFIED_FIELDS = (
    "song_id", "song_title", "chart_difficulty", "chart_variant", "game_version",
    "actual_level", "unlock_condition", "source_url", "verified_on",
)


def validate(path: Path) -> int:
    errors = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if REQUIRED - fields:
            return fail([f"Missing columns: {', '.join(sorted(REQUIRED - fields))}"])
        rows = list(reader)

    observed = Counter(row["exam_type"] for row in rows)
    for exam, (grades, slots) in EXPECTED.items():
        if observed[exam] != slots:
            errors.append(f"{exam}: expected {slots} slots, found {observed[exam]}")
        exam_rows = [r for r in rows if r["exam_type"] == exam]
        grade_counts = Counter(r["grade_no"] for r in exam_rows)
        wanted = {str(n): 4 for n in range(1, grades + 1)}
        if grade_counts != wanted:
            errors.append(f"{exam}: every grade must have exactly four slots")

    if len(rows) != 288:
        errors.append(f"Expected 288 total slots, found {len(rows)}")
    ids = [r["slot_id"] for r in rows]
    if len(set(ids)) != len(ids):
        errors.append("slot_id values must be unique")

    chart_owners = defaultdict(list)
    status_counts = Counter()
    for row in rows:
        status = row["verification_status"].strip().upper()
        status_counts[status] += 1
        if status not in {"PENDING", "VERIFIED", "NEEDS_REVIEW", "REJECTED"}:
            errors.append(f"{row['slot_id']}: unsupported verification_status {status!r}")
        if status == "VERIFIED":
            missing = [field for field in VERIFIED_FIELDS if not row[field].strip()]
            if missing:
                errors.append(f"{row['slot_id']}: VERIFIED but missing {', '.join(missing)}")
            else:
                try:
                    date.fromisoformat(row["verified_on"].strip())
                except ValueError:
                    errors.append(f"{row['slot_id']}: verified_on must be a real YYYY-MM-DD date")
                if not re.fullmatch(r"(?:[1-9]|1[0-6])\+?|β", row["actual_level"].strip()):
                    errors.append(f"{row['slot_id']}: unsupported actual_level {row['actual_level']!r}")
                parsed_url = urlparse(row["source_url"].strip())
                if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                    errors.append(f"{row['slot_id']}: source_url must be an absolute HTTP(S) URL")
                key = (row["song_id"].strip(), row["chart_difficulty"].strip().upper(),
                       row["chart_variant"].strip(), row["game_version"].strip())
                chart_owners[key].append(row)

    # Same chart identity cannot be assigned across exam types. Same song with a
    # different chart difficulty is allowed by policy.
    for key, owners in chart_owners.items():
        types = {r["exam_type"] for r in owners}
        if len(types) > 1:
            slots = ", ".join(r["slot_id"] for r in owners)
            errors.append(f"Cross-exam duplicate chart {key}: {slots}")

    print(f"Audit rows: {len(rows)} / 288")
    for exam, (_, expected_slots) in EXPECTED.items():
        print(f"  {exam}: {observed[exam]} / {expected_slots}")
    print("Statuses: " + ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items())))
    if errors:
        return fail(errors)
    print("Validation: PASS")
    return 0


def fail(errors):
    print("Validation: FAIL", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(validate(Path(sys.argv[1]) if len(sys.argv) > 1 else AUDIT))
