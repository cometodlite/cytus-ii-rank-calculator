#!/usr/bin/env python3
"""Check the final 288-slot candidate file against scope and status safeguards."""
import csv
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"

def read(name):
    with (AUDIT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def norm(s):
    s = unicodedata.normalize("NFKC", s or "").casefold()
    return "".join(c for c in s if c.isalnum())

def k(r):
    return norm(r["song_title"]), r["chart_difficulty"].strip().upper()

def main():
    final = read("final_roster_candidates_288.csv")
    base = read("roster_proposal_288.csv")
    dct = read("dct_candidate_rosters.csv")
    facts = read("bdct_song_chart_facts.csv")
    exceptions = read("final_roster_exceptions.csv")
    errors = []
    if len(final) != 288:
        errors.append(f"expected 288 rows, got {len(final)}")
    if len({r["slot_id"] for r in final}) != 288:
        errors.append("slot ids are missing or duplicated")
    expect = {"B-DCT Standard": 60, "B-DCT SV": 52, "B-DCT STT": 56, "DCT Standard": 60, "DCT MSTT": 60}
    counts = Counter(r["exam_type"] for r in final)
    if counts != Counter(expect):
        errors.append(f"exam counts mismatch: {counts}")
    if any(r["roster_status"] != "PROPOSED" for r in final):
        errors.append("a roster row is not PROPOSED")
    if any(r["playtest_status"] == "PLAYTESTED" or r["slot_verification_status"] == "VERIFIED" for r in final):
        errors.append("unearned PLAYTESTED or VERIFIED state")
    req = ("song_title", "chart_difficulty", "display_level", "selection_basis", "source_url", "source_checked_on", "conflict_status", "difficulty_review_status")
    if any(not r.get(c, "").strip() for r in final for c in req):
        errors.append("required slot metadata is blank")
    by_id = {r["slot_id"]: r for r in final}
    base_id = {r["slot_id"]: r for r in base}
    for r in final:
        if r["exam_type"] == "B-DCT Standard" and int(r["grade_no"]) <= 3:
            if r["chart_key"] != base_id[r["slot_id"]]["chart_key"]:
                errors.append(f"Standard 1-3 changed: {r['slot_id']}")
        if r["exam_type"] == "B-DCT Standard" and 4 <= int(r["grade_no"]) <= 7:
            if r["chart_key"] != base_id[r["slot_id"]]["chart_key"]:
                errors.append(f"Standard 4-7 candidate changed: {r['slot_id']}")
            if r["difficulty_review_status"] != "REQUIRED_BEFORE_APPROVAL":
                errors.append(f"Standard 4-7 difficulty review not flagged: {r['slot_id']}")
    # The two independent DCT candidate rosters stay byte-identical by slot identity.
    dct_map = {r["slot_id"]: r for r in dct}
    for slot, source in dct_map.items():
        if by_id[slot]["chart_key"] != source["candidate_chart_key"]:
            errors.append(f"DCT independent candidate changed: {slot}")
    fact_map = {k(r): r for r in facts}
    for r in final:
        if r["change_status"] == "PROPOSED_REPLACEMENT":
            fact = fact_map.get(k(r))
            if not fact:
                errors.append(f"replacement has no audited source fact: {r['slot_id']}")
            elif r["source_url"] != fact["source_url"] or r["display_level"] != fact["actual_level"]:
                errors.append(f"replacement metadata differs from source fact: {r['slot_id']}")
    owners = defaultdict(list)
    for r in final:
        owners[k(r)].append(r)
    cross = {key: group for key, group in owners.items() if len({r["exam_type"] for r in group}) > 1}
    cross_ex = [e for e in exceptions if e["exception_type"] == "CROSS_EXAM_DUPLICATE"]
    exception_slots = {s for e in cross_ex for s in e["affected_slots"].split(" | ")}
    if any(r["slot_id"] not in exception_slots for group in cross.values() for r in group):
        errors.append("cross-type collision missing from exception list")
    repeated = {key: group for key, group in owners.items() if len(group) > 1 and len({r["exam_type"] for r in group}) == 1}
    repeat_ex = [e for e in exceptions if e["exception_type"] in {"INTRA_EXAM_REPEAT", "INTRA_EXAM_REPEAT_WITH_CROSS_TYPE_CONFLICT"}]
    repeat_slots = {s for e in repeat_ex for s in e["affected_slots"].split(" | ")}
    if any(r["slot_id"] not in repeat_slots for group in repeated.values() for r in group):
        errors.append("within-exam repeat missing from exception list")
    if errors:
        print("Final roster validation: FAIL")
        for error in errors:
            print("-", error)
        return 1
    cross_repeat_keys = sum(e["exception_type"] == "INTRA_EXAM_REPEAT_WITH_CROSS_TYPE_CONFLICT" for e in exceptions)
    print(f"Final roster validation: PASS (288 slots; {len(cross)} cross-type keys/{sum(len(v) for v in cross.values())} slots; {len(repeated)} within-exam-only keys plus {cross_repeat_keys} cross-type key also repeated within an exam; all PROPOSED; no playtest/verification promotions)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
