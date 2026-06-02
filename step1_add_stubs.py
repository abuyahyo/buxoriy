# -*- coding: utf-8 -*-
"""Step 1: Insert 277 missing canonical hadiths as Arabic-only stubs.

For each canonical hadis 1..7563 missing from data.json:
  - Look up its (canonical book, canonical bab) from Islamic-OS source
  - Find the corresponding UZ kitab (using canon.json mapping)
  - Find a UZ bob in that kitab whose canon_bab_id matches; if not found,
    pick the bob whose existing hadis ids bracket the missing hadis number
  - Insert a stub: {"id": N, "matn": "", "matn_ar": "...", "tarjima_status":"missing", "canon_no": N}
  - Re-sort the bob's hadislar by id

Reversible: --revert removes all entries with tarjima_status == "missing".
"""
import json, os, sys, io, sqlite3, shutil, argparse
from collections import defaultdict
import bisect

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data.json')
BACKUP = os.path.join(ROOT, 'data.json.bak2')

ap = argparse.ArgumentParser()
ap.add_argument('--revert', action='store_true')
args = ap.parse_args()

with open(DATA, 'r', encoding='utf-8') as f:
    db = json.load(f)

if args.revert:
    n = 0
    for k in db:
        for bo in k.get('boblar', []):
            before = len(bo.get('hadislar', []))
            bo['hadislar'] = [h for h in bo.get('hadislar', []) if h.get('tarjima_status') != 'missing']
            n += before - len(bo['hadislar'])
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Reverted: removed {n} stub hadiths')
    sys.exit(0)

shutil.copy(DATA, BACKUP)
print(f'Backup: {BACKUP}')

# Collect existing hadis IDs
existing_ids = set()
for k in db:
    for bo in k.get('boblar', []):
        for h in bo.get('hadislar', []):
            existing_ids.add(int(h['id']) if isinstance(h['id'], (int, float)) and float(h['id']).is_integer() else h['id'])

missing = sorted(set(range(1, 7564)) - existing_ids)
print(f'Missing canonical hadiths: {len(missing)}')

# Load canonical hadis → (book, bab, arabic_text, arabic_bab_name)
con = sqlite3.connect(os.path.join(ROOT, 'bukhari_qitab.db'))
cur = con.cursor()
canon_info = {}
for r in cur.execute("""
    SELECT hadithNumber, bookNumber, babID, arabicBabName, arabicText
    FROM bukhari
    WHERE hadithNumber IS NOT NULL AND hadithNumber != ''
"""):
    # hadithNumber can be a compound like "1008, 1009" — one row covers multiple ids
    parts = [p.strip() for p in str(r[0]).split(',')]
    for p in parts:
        try:
            hn = int(float(p))
        except ValueError:
            continue
        canon_info[hn] = {
            'book': int(r[1]),
            'bab': r[2],
            'bab_name': (r[3] or '').strip(),
            'text': (r[4] or '').strip(),
        }
con.close()

# canon kitab id -> UZ kitab id (forward mapping)
canon_to_uz_kitab = defaultdict(list)
for k in db:
    if k.get('canon_kitab'):
        canon_to_uz_kitab[k['canon_kitab']].append(k['id'])

# For each missing hadis, find a place to put it
inserted = 0
skipped_no_canon = 0
skipped_no_kitab = 0
inserted_by_bab = 0
inserted_by_range = 0
new_bobs = 0

# Build a quick lookup: for each (uz_kitab_id, canon_bab_id) -> bob index
kitab_lookup = {}
for k_idx, k in enumerate(db):
    by_bab = defaultdict(list)  # canon_bab_id -> [bob_index in k['boblar']]
    by_range = []  # list of (bob_index, min_hadis, max_hadis) for hadis-range fallback
    for b_idx, bo in enumerate(k['boblar']):
        cb = bo.get('canon_bab_id')
        if cb is not None:
            by_bab[cb].append(b_idx)
        h_ids = [int(h['id']) for h in bo.get('hadislar', []) if isinstance(h['id'], (int, float))]
        if h_ids:
            by_range.append((b_idx, min(h_ids), max(h_ids)))
    by_range.sort(key=lambda x: x[1])
    kitab_lookup[k['id']] = (by_bab, by_range)

for hid in missing:
    info = canon_info.get(hid)
    if not info:
        skipped_no_canon += 1
        continue
    canon_bk = info['book']
    canon_bab = info['bab']

    uz_kitabs = canon_to_uz_kitab.get(canon_bk)
    if not uz_kitabs:
        skipped_no_kitab += 1
        continue

    # Pick the UZ kitab: if canon_bk == 86 (Hudud), we have two UZ kitabs
    # (86 and 87). Use hadis range to decide: UZ-86 has 6772-6801, UZ-87 has 6802-6859.
    # For canon hadis falling in 6802-6859, put in UZ-87; otherwise UZ-86.
    chosen_uz_kitab = uz_kitabs[0]
    if len(uz_kitabs) > 1:
        # Find by hadis range
        for uk in uz_kitabs:
            k = next(kk for kk in db if kk['id'] == uk)
            h_ids = []
            for bo in k['boblar']:
                for h in bo.get('hadislar', []):
                    if isinstance(h['id'], (int, float)):
                        h_ids.append(int(h['id']))
            if h_ids and min(h_ids) <= hid <= max(h_ids):
                chosen_uz_kitab = uk
                break

    # Find target kitab in db
    target_k = next(k for k in db if k['id'] == chosen_uz_kitab)
    by_bab, by_range = kitab_lookup[chosen_uz_kitab]

    stub = {
        'id': hid,
        'matn': '',
        'matn_ar': info['text'],
        'tarjima_status': 'missing',
        'canon_no': hid,
    }

    # Strategy 1: bob with matching canon_bab_id
    if canon_bab in by_bab:
        b_idx = by_bab[canon_bab][0]
        target_bob = target_k['boblar'][b_idx]
        target_bob['hadislar'].append(stub)
        target_bob['hadislar'].sort(key=lambda h: float(h['id']) if isinstance(h['id'], (int, float)) else 9999)
        inserted_by_bab += 1
        inserted += 1
        continue

    # Strategy 2: insert in bob whose hadis range covers (or is closest to) this id
    target_b_idx = None
    for b_idx, lo, hi in by_range:
        if lo <= hid <= hi:
            target_b_idx = b_idx
            break
    if target_b_idx is None and by_range:
        # Find bob with closest range (by lower bound)
        positions = [r[1] for r in by_range]
        ip = bisect.bisect_left(positions, hid)
        if ip == 0:
            target_b_idx = by_range[0][0]
        elif ip >= len(by_range):
            target_b_idx = by_range[-1][0]
        else:
            # Pick whichever bob's range is closer
            prev_b = by_range[ip-1]
            next_b = by_range[ip]
            if abs(prev_b[2] - hid) <= abs(next_b[1] - hid):
                target_b_idx = prev_b[0]
            else:
                target_b_idx = next_b[0]

    if target_b_idx is None:
        # Kitab has no bob with hadis; create a new bob
        new_bob = {
            'id': len(target_k['boblar']) + 1,
            'nomi': f"{len(target_k['boblar'])+1}-БОБ",
            'canon_bab_id': canon_bab,
            'canon_bab_nomi_ar': info['bab_name'],
            'hadislar': [stub],
        }
        target_k['boblar'].append(new_bob)
        new_bobs += 1
        inserted += 1
    else:
        target_bob = target_k['boblar'][target_b_idx]
        target_bob['hadislar'].append(stub)
        target_bob['hadislar'].sort(key=lambda h: float(h['id']) if isinstance(h['id'], (int, float)) else 9999)
        inserted_by_range += 1
        inserted += 1

print(f'\n=== Insertion summary ===')
print(f'Inserted by matching canon_bab_id:  {inserted_by_bab}')
print(f'Inserted by hadis-range fallback:   {inserted_by_range}')
print(f'New bobs created:                   {new_bobs}')
print(f'Total inserted:                     {inserted}')
print(f'Skipped (no canon info):            {skipped_no_canon}')
print(f'Skipped (no UZ kitab for canon):    {skipped_no_kitab}')

# Total hadis after
total = sum(len(bo.get('hadislar', [])) for k in db for bo in k.get('boblar', []))
print(f'\nTotal hadis entries now: {total} (was 7301; expected ≈ 7301 + {inserted})')

with open(DATA, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
print(f'data.json: {os.path.getsize(DATA)} bytes')
