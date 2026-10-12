#!/usr/bin/env python3
"""Embed the audited CSV roster in the single-file GitHub Pages calculator."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "audit" / "final_roster_candidates_288.csv"
EXCEPTIONS_PATH = ROOT / "audit" / "final_roster_exceptions.csv"
HTML_PATH = ROOT / "index.html"
START = "// BEGIN GENERATED ROSTER DATA"
END = "// END GENERATED ROSTER DATA"

with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
if len(rows) != 288:
    raise SystemExit(f"Expected 288 roster slots, got {len(rows)}")
expected_exam_counts = {
    "B-DCT Standard": 60,
    "B-DCT SV": 52,
    "B-DCT STT": 56,
    "DCT Standard": 60,
    "DCT MSTT": 60,
}
exam_counts = Counter(row.get("exam_type", "") for row in rows)
if dict(exam_counts) != expected_exam_counts:
    raise SystemExit(f"Unexpected exam slot counts: {dict(exam_counts)}")
grade_counts = Counter((row.get("exam_type", ""), row.get("grade_no", "")) for row in rows)
if len(grade_counts) != 72 or any(count != 4 for count in grade_counts.values()):
    raise SystemExit("Every one of the 72 grades must have exactly four slots")
if any(row.get("roster_status") != "PROPOSED" for row in rows):
    raise SystemExit("Only PROPOSED roster rows can be embedded")
if any(row.get("playtest_status") == "PLAYTESTED" or row.get("slot_verification_status") == "VERIFIED" for row in rows):
    raise SystemExit("Roster contains an unsupported verification promotion")
required_fields = ("song_title", "chart_difficulty", "display_level", "source_url", "source_checked_on",
                   "source_fact_status", "slot_verification_status", "playtest_status")
if any(not row.get(field, "").strip() for row in rows for field in required_fields):
    raise SystemExit("A roster slot is missing displayed source or verification metadata")
with EXCEPTIONS_PATH.open(encoding="utf-8-sig", newline="") as f:
    exception_rows = list(csv.DictReader(f))
required_duplicate_keys = {"kanata#CHAOS", "drg#HARD", "droppinglightspeed#CHAOS"}
present_duplicate_keys = {row.get("chart_key") for row in exception_rows if row.get("exception_type") == "CROSS_EXAM_DUPLICATE"}
if not required_duplicate_keys.issubset(present_duplicate_keys):
    raise SystemExit("One or more required cross-exam duplicate warnings are missing")

block = (START + "\nconst ROSTER = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n"
         + "const ROSTER_EXCEPTIONS = " + json.dumps(exception_rows, ensure_ascii=False, separators=(",", ":")) + ";\n"
         + END)
html = HTML_PATH.read_text(encoding="utf-8")
if START in html and END in html:
    prefix, rest = html.split(START, 1)
    _, suffix = rest.split(END, 1)
    html = prefix + block + suffix
else:
    marker = "const DATA="
    index = html.index(marker)
    line_end = html.index("\n", index)
    html = html[:line_end + 1] + block + "\n" + html[line_end + 1:]
HTML_PATH.write_text(html, encoding="utf-8")
print(f"Embedded {len(rows)} PROPOSED roster slots into index.html")
