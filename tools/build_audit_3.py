#!/usr/bin/env python3
"""Build review-only CYTUS II 3rd-audit tables from source-confirmed 2nd-audit data."""
import csv
import re
from collections import defaultdict
from statistics import median
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit'
CHECKED_ON = '2026-10-12'


def read(name):
    with (AUDIT / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write(name, rows, fields=None):
    if fields is None:
        fields = list(rows[0]) if rows else []
    with (AUDIT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def level(value):
    s = (value or '').strip()
    if not s or not s[0].isdigit():
        return None
    return int(s.rstrip('+')) + (0.5 if s.endswith('+') else 0)


def duration(value):
    match = re.search(r'(\d+):(\d{2})', value or '')
    return int(match.group(1)) * 60 + int(match.group(2)) if match else None


def density(fact):
    n, secs = int(fact.get('note_count') or 0), duration(fact.get('length', ''))
    return round(n * 60 / secs, 1) if n and secs else ''


def target_distance(a, b):
    av, bv = level(a), level(b)
    return abs(av - bv) if av is not None and bv is not None else 99

# Normalize the second-audit chart facts to the requested state vocabulary.
for filename, status_field in [
    ('chart_slots.csv', 'candidate_chart_fact_status'),
    ('bdct_song_chart_facts.csv', 'fact_status'),
    ('chart_fact_records.csv', 'fact_status'),
    ('bdct_duplicate_replacement_candidates.csv', 'candidate_status'),
    ('dct_candidate_rosters.csv', 'candidate_status'),
]:
    rows = read(filename)
    for row in rows:
        if row.get(status_field) == 'CHART_CONFIRMED':
            row[status_field] = 'SOURCE_CONFIRMED'
        if filename == 'dct_candidate_rosters.csv':
            row['candidate_review_status'] = 'PENDING'
            row['playtest_status'] = 'PENDING'
            row['slot_verification_status'] = 'PENDING'
            row['review_limitation'] = 'Target level matches source; note structure, rhythm, hand usage, and performance-purpose suitability are not evidenced.'
    write(filename, rows)

slots = read('chart_slots.csv')
facts = read('bdct_song_chart_facts.csv')
overlaps = read('bdct_overlap_report.csv')
dct = read('dct_candidate_rosters.csv')
fact_by_song = defaultdict(list)
for fact in facts:
    fact_by_song[fact['source_song_key']].append(fact)

# Standard grades 4-7: select the closest source-confirmed chart on each original song,
# then order each quartet by source level and density for a smooth progression.
standard = []
for grade in range(4, 8):
    group = [s for s in slots if s['exam_type'] == 'B-DCT Standard' and int(s['grade_no']) == grade]
    chosen = []
    for slot in group:
        options = [f for f in fact_by_song[slot['candidate_source_song_key']] if level(f['actual_level']) is not None]
        best = min(options, key=lambda f: (target_distance(f['actual_level'], slot['target_level']),
                                           f['chart_difficulty'] in {'GLITCH', 'CRASH'},
                                           int(f.get('note_count') or 0)))
        chosen.append((slot, best))
    chosen.sort(key=lambda pair: (level(pair[1]['actual_level']), density(pair[1]) if density(pair[1]) != '' else 0,
                                  pair[1]['song_title']))
    targets = sorted((s['target_level'] for s in group), key=lambda x: level(x))
    for new_pos, ((slot, fact), target) in enumerate(zip(chosen, targets), 1):
        chart_key = fact['chart_key']
        other_types = sorted({s['exam_type'] for s in slots if s['exam_type'] != 'B-DCT Standard' and s['candidate_chart_key'] == chart_key})
        d = density(fact)
        standard.append({
            'grade_no': str(grade), 'grade_label': slot['grade_label'], 'proposed_position': str(new_pos),
            'original_slot_id': slot['slot_id'], 'original_position': slot['slot_position'],
            'original_song_title': slot['song_title'], 'original_assumed_chart': slot['candidate_chart_key'],
            'original_assumed_level': slot['candidate_chart_level'], 'target_level_for_position': target,
            'proposed_song_title': fact['song_title'], 'proposed_chart_key': chart_key,
            'proposed_chart_difficulty': fact['chart_difficulty'], 'proposed_level': fact['actual_level'],
            'signed_level_delta': f"{level(fact['actual_level']) - level(target):+.1f}",
            'note_count': fact['note_count'], 'bpm': fact['bpm'], 'length': fact['length'],
            'notes_per_min_proxy': d, 'unlock_condition': fact['unlock_condition'],
            'source_url': fact['source_url'], 'source_checked_on': fact['source_checked_on'],
            'source_confidence': fact['source_confidence'], 'source_status': 'SOURCE_CONFIRMED',
            'candidate_review_status': 'PENDING', 'playtest_status': 'PENDING',
            'current_cross_type_conflict': ', '.join(other_types),
            'technical_review': 'Chart event pattern, rhythm, hand placement, and stamina need gameplay/chart-structure review.',
            'slot_verification_status': 'PENDING',
        })
write('bdct_standard_4_7_recomposition_candidates.csv', standard)

# Cross-exam overlaps: indicate a provisional owner solely by average level fit.
# This is a triage cue, never a finalized decision.
retention = {}
overlap_summary = []
for item in overlaps:
    key = item['candidate_chart_key']
    affected = [s for s in slots if s['candidate_chart_key'] == key]
    per_type = defaultdict(list)
    for s in affected:
        gap = target_distance(item['actual_level'], s['target_level'])
        per_type[s['exam_type']].append(gap)
    averages = {t: sum(gaps) / len(gaps) for t, gaps in per_type.items()}
    best = min(averages.values())
    owners = sorted(t for t, avg in averages.items() if avg == best)
    retention[key] = owners[0] if len(owners) == 1 else ''
    overlap_summary.append({
        'candidate_chart_key': key, 'song_title': item['song_title'], 'difficulty': item['candidate_difficulty'],
        'source_level': item['actual_level'], 'candidate_slot_count': item['candidate_slot_count'],
        'exam_types': item['exam_types'], 'candidate_slots': item['candidate_slots'],
        'average_level_gap_by_type': ' | '.join(f'{t}: {averages[t]:.2f}' for t in sorted(averages)),
        'provisional_retain_type_by_level_fit': retention[key] or 'TIE_REQUIRES_REVIEW',
        'score_stability_vs_tp_fit': 'NOT_ASSESSED; chart pattern data unavailable',
        'source_url': item['source_url'], 'source_confidence': item['source_confidence'],
        'source_status': 'SOURCE_CONFIRMED', 'candidate_review_status': 'PENDING',
        'playtest_status': 'PENDING', 'slot_verification_status': 'PENDING',
        'notes': '37-key list is conditional on app difficulty heuristic; ownership cue minimizes level gap only and needs purpose/playtest review.'
    })
write('bdct_sv_stt_overlap_resolution.csv', overlap_summary)

# Per-slot alternatives for occurrences that would be moved away from the provisional owner.
used_by_other_types = defaultdict(set)
for s in slots:
    used_by_other_types[s['candidate_chart_key']].add(s['exam_type'])
resolution_options = []
for item in overlaps:
    key = item['candidate_chart_key']
    keep_type = retention[key]
    affected = [s for s in slots if s['candidate_chart_key'] == key]
    for slot in affected:
        if keep_type and slot['exam_type'] == keep_type:
            continue
        source_key = slot['candidate_source_song_key']
        options = [f for f in fact_by_song[source_key] if f['chart_key'] != key and level(f['actual_level']) is not None]
        options.sort(key=lambda f: (bool(used_by_other_types[f['chart_key']] - {slot['exam_type']}),
                                   target_distance(f['actual_level'], slot['target_level']),
                                   int(f.get('note_count') or 0)))
        for rank, f in enumerate(options[:3], 1):
            conflicts = sorted(used_by_other_types[f['chart_key']] - {slot['exam_type']})
            resolution_options.append({
                'overlap_chart_key_to_resolve': key, 'affected_slot_id': slot['slot_id'],
                'exam_type': slot['exam_type'], 'grade_label': slot['grade_label'],
                'slot_position': slot['slot_position'], 'song_title': f['song_title'],
                'target_level': slot['target_level'], 'current_candidate_level': item['actual_level'],
                'provisional_retain_type': keep_type or 'TIE_REQUIRES_REVIEW',
                'alternative_rank': str(rank), 'candidate_chart_key': f['chart_key'],
                'candidate_difficulty': f['chart_difficulty'], 'candidate_level': f['actual_level'],
                'level_gap': f'{target_distance(f["actual_level"], slot["target_level"]):.1f}',
                'note_count': f['note_count'], 'bpm': f['bpm'], 'length': f['length'],
                'notes_per_min_proxy': density(f), 'unlock_condition': f['unlock_condition'],
                'currently_used_by_other_exam_types': ', '.join(conflicts),
                'source_url': f['source_url'], 'source_checked_on': f['source_checked_on'],
                'source_status': 'SOURCE_CONFIRMED', 'candidate_review_status': 'PENDING',
                'playtest_status': 'PENDING', 'slot_verification_status': 'PENDING',
                'technical_review': 'Do not select by level alone; compare note structure and exam-purpose suitability.'
            })
write('bdct_cross_type_replacement_options.csv', resolution_options)

# DCT candidate quality screen: source facts + exact rating + within-grade note-density context.
review = []
for exam in ('DCT Standard', 'DCT MSTT'):
    for grade in range(1, 16):
        group = [r for r in dct if r['exam_type'] == exam and int(r['grade_no']) == grade]
        vals = [float(r['notes_per_min']) for r in group if r['notes_per_min']]
        grade_median = median(vals) if vals else 0
        for row in group:
            npm = float(row['notes_per_min']) if row['notes_per_min'] else 0
            rel = round(npm / grade_median, 3) if grade_median else ''
            review.append({
                'slot_id': row['slot_id'], 'exam_type': exam, 'grade_no': row['grade_no'],
                'grade_label': row['grade_label'], 'slot_position': row['slot_position'],
                'song_title': row['song_title'], 'candidate_chart_key': row['candidate_chart_key'],
                'chart_difficulty': row['chart_difficulty'], 'target_level': row['target_level'],
                'source_level': row['actual_level'], 'target_fit': 'EXACT', 'unlock_condition': row['unlock_condition'],
                'note_count': row['note_count'], 'bpm': row['bpm'], 'length': row['length'],
                'notes_per_min_proxy': row['notes_per_min'], 'density_vs_grade_median': rel,
                'technical_screen': 'Metadata only; note types, rhythm, hand travel, and endurance not established.',
                'exam_purpose_screen': 'PENDING', 'source_url': row['source_url'],
                'source_checked_on': row['source_checked_on'], 'source_confidence': row['source_confidence'],
                'source_status': 'SOURCE_CONFIRMED', 'candidate_review_status': 'PENDING',
                'playtest_status': 'PENDING', 'slot_verification_status': 'PENDING',
            })
write('dct_candidate_review.csv', review)

# Grade-by-grade level trend, keeping app mappings separate from DCT proposals.
progression = []
exam_grade_counts = {'B-DCT Standard': 15, 'B-DCT SV': 13, 'B-DCT STT': 14,
                     'DCT Standard': 15, 'DCT MSTT': 15}
for exam, grade_count in exam_grade_counts.items():
    for grade in range(1, grade_count + 1):
        if exam.startswith('B-DCT'):
            group = sorted((r for r in slots if r['exam_type'] == exam and int(r['grade_no']) == grade),
                           key=lambda r: int(r['slot_position']))
            ratings = [r['candidate_chart_level'] for r in group]
            targets = [r['target_level'] for r in group]
            kinds = [r['candidate_chart_key'].split('#')[-1] for r in group]
            densities = [density({'note_count': r['candidate_note_count'], 'length': r['candidate_length']}) for r in group]
            origin = 'CURRENT_APP_DIFFICULTY_HEURISTIC'
        else:
            group = sorted((r for r in dct if r['exam_type'] == exam and int(r['grade_no']) == grade),
                           key=lambda r: int(r['slot_position']))
            ratings = [r['actual_level'] for r in group]
            targets = [r['target_level'] for r in group]
            kinds = [r['chart_difficulty'] for r in group]
            densities = [density({'note_count': r['note_count'], 'length': r['length']}) for r in group]
            origin = 'SOURCE_CONFIRMED_DCT_PROPOSAL'
        pairs = [(level(rating), level(target)) for rating, target in zip(ratings, targets) if level(rating) is not None and level(target) is not None]
        actual_numeric = [level(x) for x in ratings if level(x) is not None]
        density_values = [float(x) for x in densities if x != '']
        if exam == 'B-DCT Standard' and grade <= 3:
            assessment = 'Keep existing grade; no new v1.3 target defined.'
        elif exam.startswith('B-DCT'):
            assessment = 'Current app mapping only; assess against temporary target and confirm actual assignment.'
        else:
            assessment = 'All four source chart levels match the provisional target; pattern/purpose review pending.'
        progression.append({
            'exam_type': exam, 'grade_no': str(grade), 'grade_label': group[0]['grade_label'] if group else '',
            'level_data_basis': origin, 'target_levels_by_position': ' / '.join(targets),
            'candidate_levels_by_position': ' / '.join(ratings), 'chart_kinds_by_position': ' / '.join(kinds),
            'above_target_count': str(sum(a > t for a, t in pairs)),
            'at_target_count': str(sum(a == t for a, t in pairs)),
            'below_target_count': str(sum(a < t for a, t in pairs)),
            'levels_nondecreasing_in_slot_order': 'YES' if len(actual_numeric) == len(ratings) and actual_numeric == sorted(actual_numeric) else 'NO_OR_SPECIAL_LABEL',
            'notes_per_min_range_proxy': f'{min(density_values):.1f}-{max(density_values):.1f}' if density_values else '',
            'assessment': assessment, 'source_status': 'SOURCE_CONFIRMED' if exam.startswith('DCT') or group else 'PENDING',
            'candidate_review_status': 'PENDING', 'playtest_status': 'PENDING', 'slot_verification_status': 'PENDING',
        })
write('grade_level_progression.csv', progression)

# Unique chart-level playtest queue across proposed Standard, overlap, and DCT candidates.
queue = {}
def add_queue(key, song, difficulty, rating, notes, bpm, length, url, exam, focus):
    if not key:
        return
    if key not in queue:
        queue[key] = {'candidate_chart_key': key, 'song_title': song, 'chart_difficulty': difficulty,
                      'source_level': rating, 'note_count': notes, 'bpm': bpm, 'length': length,
                      'notes_per_min_proxy': '', 'source_url': url, 'exam_types_to_consider': set(),
                      'playtest_focus': set(), 'source_status': 'SOURCE_CONFIRMED',
                      'candidate_review_status': 'PENDING', 'playtest_status': 'PENDING',
                      'slot_verification_status': 'PENDING'}
    queue[key]['exam_types_to_consider'].add(exam)
    queue[key]['playtest_focus'].add(focus)
for row in standard:
    add_queue(row['proposed_chart_key'], row['proposed_song_title'], row['proposed_chart_difficulty'],
              row['proposed_level'], row['note_count'], row['bpm'], row['length'], row['source_url'],
              'B-DCT Standard', 'level-fit, rhythm, hand-use, stamina, score/TP behavior')
for slot in slots:
    if not slot['exam_type'].startswith('B-DCT') or not slot['candidate_chart_key']:
        continue
    focus = ('score stability, note density, rhythm, combo continuity' if slot['exam_type'] == 'B-DCT SV'
             else 'TP precision, timing patterns, note types, endurance' if slot['exam_type'] == 'B-DCT STT'
             else 'difficulty progression, rhythm, hand use, stamina')
    add_queue(slot['candidate_chart_key'], slot['candidate_source_title'],
              slot['candidate_chart_key'].split('#')[-1], slot['candidate_chart_level'],
              slot['candidate_note_count'], slot['candidate_bpm'], slot['candidate_length'],
              slot['candidate_source_page'], slot['exam_type'], focus)
for item in overlaps:
    add_queue(item['candidate_chart_key'], item['song_title'], item['candidate_difficulty'],
              item['actual_level'], '', '', '', item['source_url'], item['exam_types'],
              'cross-exam overlap, score stability, TP precision')
for row in dct:
    add_queue(row['candidate_chart_key'], row['song_title'], row['chart_difficulty'], row['actual_level'],
              row['note_count'], row['bpm'], row['length'], row['source_url'], row['exam_type'],
              'comprehensive handling or M.PERFECT accuracy, pattern diversity, master endurance')
for row in resolution_options:
    add_queue(row['candidate_chart_key'], row['song_title'], row['candidate_difficulty'], row['candidate_level'],
              row['note_count'], row['bpm'], row['length'], row['source_url'], row['exam_type'],
              'replacement-option chart; resolve overlap, rhythm, hand use, score/TP suitability')
fact_by_chart = {r['chart_key']: r for r in facts}
for key, row in queue.items():
    fact = fact_by_chart.get(key)
    if fact:
        row['note_count'] = row['note_count'] or fact['note_count']
        row['bpm'] = row['bpm'] or fact['bpm']
        row['length'] = row['length'] or fact['length']
        row['source_url'] = row['source_url'] or fact['source_url']
        if not row['source_level']:
            row['source_level'] = fact['actual_level']
    row['notes_per_min_proxy'] = density({'note_count': row['note_count'], 'length': row['length']})
    row['exam_types_to_consider'] = ' | '.join(sorted(row['exam_types_to_consider']))
    row['playtest_focus'] = ' | '.join(sorted(row['playtest_focus']))
write('chart_playtest_queue.csv', sorted(queue.values(), key=lambda x: x['candidate_chart_key']))
print(f'Standard proposals={len(standard)}; overlap keys={len(overlap_summary)}; overlap alternatives={len(resolution_options)}; DCT review rows={len(review)}; unique playtest charts={len(queue)}')
