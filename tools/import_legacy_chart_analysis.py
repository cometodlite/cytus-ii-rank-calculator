#!/usr/bin/env python3
"""Import chart-analysis summaries from the archived community viewer into audit-only CSV."""

import argparse
import csv
import json
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
REPO_URL = "https://github.com/harlos0517/cytus2-charts"
REPO_COMMIT = "07722a2d0e90e65611cd8d72a4220f91f614fbeb"
SNAPSHOT_DATE = "2021-07-28"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def norm(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return "".join(c for c in value if c.isalnum())


def num_level(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", required=True, help="Path to archived web/songs_analyzed.json")
    args = parser.parse_args()
    source = json.loads(Path(args.source_json).read_text(encoding="utf-8"))
    index = defaultdict(list)
    for record in source:
        key = (norm(record.get("song", {}).get("name")), record.get("diff", {}).get("name", "").upper())
        index[key].append(record)

    queue = read_csv(AUDIT / "chart_playtest_queue.csv")
    out = []
    for q in queue:
        key = (norm(q.get("song_title")), q.get("chart_difficulty", "").upper())
        hits = [r for r in index[key] if int(r.get("numOf", {}).get("note", -1)) == int(q.get("note_count") or 0)]
        # Duplicate chart identifiers are retained as a data ambiguity instead of silently selecting one.
        exact = [r for r in hits if num_level(r.get("diff", {}).get("level")) == num_level(q.get("source_level", "").rstrip("+"))]
        selected = exact[0] if len(exact) == 1 else (hits[0] if len(hits) == 1 else None)
        match = "LEVEL_AND_NOTE_COUNT_MATCH" if selected and exact else ("NOTE_COUNT_MATCH_LEVEL_DIFF" if selected else ("AMBIGUOUS_MATCH" if hits else "NO_ITEM_LEVEL_MATCH"))
        if selected:
            pp = selected.get("notePerPage", {})
            notes = selected.get("notes", []) + [0] * max(0, 8-len(selected.get("notes", [])))
            rhythms = selected.get("topRhythms", [])
            rhythm_summary = " | ".join(f'{x.get("pattern", "")} ({x.get("count", "")} hits, {x.get("beats", "")} beats)' for x in rhythms[:3])
            desk = "DESK_REVIEWED"
            level = selected.get("diff", {}).get("level", "")
            count = selected.get("numOf", {}).get("note", "")
            detail = "Historical chart-analysis summary inspected: note-type counts, page density, hold range, simultaneous grouping, algorithmic finger-overlap estimate, and top rhythm patterns. Not a current-version guarantee or playtest."
            vals = {
                "snapshot_level": level, "snapshot_note_count": count,
                "snapshot_click_count": notes[0], "snapshot_hold_count": notes[1], "snapshot_long_count": notes[2],
                "snapshot_dragh_count": notes[3], "snapshot_drag_count": notes[4], "snapshot_flick_count": notes[5],
                "snapshot_cdragh_count": notes[6], "snapshot_cdrag_count": notes[7],
                "snapshot_note_density_avg": pp.get("density", ""), "snapshot_note_density_max": pp.get("densityMax", ""),
                "snapshot_rhythm_density_avg": pp.get("rDensity", ""), "snapshot_rhythm_density_max": pp.get("rDensityMax", ""),
                "snapshot_max_notes_per_page": pp.get("max", ""), "snapshot_max_rhythm_notes_per_page": pp.get("rMax", ""),
                "snapshot_hold_beats_min": selected.get("holdBeat", {}).get("min", ""),
                "snapshot_hold_beats_max": selected.get("holdBeat", {}).get("max", ""),
                "snapshot_max_simultaneous_sibling_group": selected.get("maxSibling", ""),
                "snapshot_algorithmic_max_finger_proxy": selected.get("maxFinger", ""),
                "snapshot_rhythm_count": selected.get("rhyTotal", ""), "snapshot_top_rhythm_patterns": rhythm_summary,
            }
        else:
            desk = "PENDING"
            match = "AMBIGUOUS_MATCH" if hits else "NO_ITEM_LEVEL_MATCH"
            detail = "No unique archived summary with matching title, difficulty, and note count was available; do not infer chart structure."
            vals = {k: "" for k in ["snapshot_level", "snapshot_note_count", "snapshot_click_count", "snapshot_hold_count", "snapshot_long_count", "snapshot_dragh_count", "snapshot_drag_count", "snapshot_flick_count", "snapshot_cdragh_count", "snapshot_cdrag_count", "snapshot_note_density_avg", "snapshot_note_density_max", "snapshot_rhythm_density_avg", "snapshot_rhythm_density_max", "snapshot_max_notes_per_page", "snapshot_max_rhythm_notes_per_page", "snapshot_hold_beats_min", "snapshot_hold_beats_max", "snapshot_max_simultaneous_sibling_group", "snapshot_algorithmic_max_finger_proxy", "snapshot_rhythm_count", "snapshot_top_rhythm_patterns"]}
        out.append({"candidate_chart_key": q["candidate_chart_key"], "song_title": q["song_title"], "chart_difficulty": q["chart_difficulty"],
                    "current_catalog_level": q["source_level"], "current_catalog_note_count": q["note_count"],
                    "desk_review_status": desk, "snapshot_match_status": match, **vals,
                    "source_repository": REPO_URL, "source_commit": REPO_COMMIT, "source_snapshot_date": SNAPSHOT_DATE,
                    "review_scope_and_limit": detail, "playtest_status": "PENDING"})
    with (AUDIT / "chart_desk_review.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(out)
    print(f"Imported historical chart-analysis records: {sum(r['desk_review_status']=='DESK_REVIEWED' for r in out)} reviewed; {sum(r['desk_review_status']=='PENDING' for r in out)} pending without a matching snapshot")


if __name__ == "__main__":
    main()
