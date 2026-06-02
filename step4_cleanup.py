# -*- coding: utf-8 -*-
"""Step 4: Cleanup remaining 9 duplicates + 9 strays in data.json.

Approach:
  - Strays: hadis whose canonical book differs from its UZ kitab.
    Move it to the canonical UZ kitab (find a bob with matching canon_bab_id,
    fall back to closest-range bob).
  - Duplicates: hadis present in multiple (kitab, bob) locations.
    Keep the canonical occurrence (the one whose UZ kitab matches canon_kitab),
    remove others. If multiple canonical occurrences, keep the earliest bob.

Reversible: --revert restores data.json.bak5.
"""
import json, os, sys, io, sqlite3, shutil, argparse
from collections import defaultdict
import bisect

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data.json')
BACKUP = os.path.join(ROOT, 'data.json.bak5')

ap = argparse.ArgumentParser()
ap.add_argument('--revert', action='store_true')
args = ap.parse_args()

if args.revert:
    if not os.path.exists(BACKUP):
        print('No backup'); sys.exit(1)
    shutil.copy(BACKUP, DATA)
    print('Reverted'); sys.exit(0)

shutil.copy(DATA, BACKUP)

with open(DATA, 'r', encoding='utf-8') as f:
    db = json.load(f)

# Get hadis -> canonical book mapping
con = sqlite3.connect(os.path.join(ROOT, 'bukhari_qitab.db'))
cur = con.cursor()
hadis_to_canon = {}  # hadis_id -> (canon_book, canon_bab)
for r in cur.execute("SELECT hadithNumber, bookNumber, babID FROM bukhari WHERE hadithNumber != ''"):
    for p in str(r[0]).split(','):
        try:
            hn = int(float(p.strip()))
            hadis_to_canon[hn] = (int(r[1]), r[2])
        except ValueError:
            pass
con.close()

# Build kitab lookup
db_by_id = {k['id']: k for k in db}
canon_to_uz_kitab = {}
for k in db:
    if k.get('canon_kitab'):
        canon_to_uz_kitab[k['canon_kitab']] = k['id']

# Collect all (kid, bid, h) locations per hadis_id
loc = defaultdict(list)
for k in db:
    for bo in k['boblar']:
        for h in bo['hadislar']:
            hid = h['id']
            if isinstance(hid, float) and hid.is_integer():
                hid = int(hid)
            loc[hid].append((k['id'], bo['id'], h))

# 1. Resolve duplicates: keep one canonical, remove others
removed_dup = 0
for hid, locs in list(loc.items()):
    if not isinstance(hid, int) or len(locs) <= 1:
        continue
    canon = hadis_to_canon.get(hid)
    if not canon:
        continue
    canon_uz_kitab = canon_to_uz_kitab.get(canon[0])
    if canon_uz_kitab is None:
        continue

    # Find the "best" location: canonical kitab, lowest bob id, prefer non-stub
    def rank(item):
        kid, bid, h = item
        in_canon_kitab = (kid == canon_uz_kitab)
        is_stub = h.get('tarjima_status') == 'missing'
        return (not in_canon_kitab, is_stub, bid)  # smaller is better
    locs.sort(key=rank)
    keeper = locs[0]
    losers = locs[1:]

    # Remove losers
    for kid, bid, h in losers:
        k = db_by_id[kid]
        for bo in k['boblar']:
            if bo['id'] == bid:
                bo['hadislar'] = [hh for hh in bo['hadislar'] if not (hh is h or (hh.get('id') == hid and hh.get('tarjima_status', '') == h.get('tarjima_status', '')))]
                removed_dup += 1
                break

print(f'Removed duplicate entries: {removed_dup}')

# Rebuild loc to reflect duplicate removal
loc = defaultdict(list)
for k in db:
    for bo in k['boblar']:
        for h in bo['hadislar']:
            hid = h['id']
            if isinstance(hid, float) and hid.is_integer():
                hid = int(hid)
            loc[hid].append((k['id'], bo['id'], h))

# 2. Move strays to canonical kitab
moved_strays = 0
to_move = []
for k in db:
    for bo in k['boblar']:
        for h in bo['hadislar']:
            hid = h['id']
            if isinstance(hid, float):
                if hid.is_integer():
                    hid = int(hid)
                else:
                    continue
            canon = hadis_to_canon.get(hid)
            if not canon:
                continue
            canon_uz_kitab = canon_to_uz_kitab.get(canon[0])
            if canon_uz_kitab is None or canon_uz_kitab == k['id']:
                continue
            to_move.append((hid, k['id'], bo['id'], h, canon_uz_kitab, canon[1]))

for hid, kid, bid, h, target_kitab, target_canon_bab in to_move:
    # Remove from current bob
    src_k = db_by_id[kid]
    for bo in src_k['boblar']:
        if bo['id'] == bid:
            bo['hadislar'] = [hh for hh in bo['hadislar'] if not (hh is h)]
            break
    # Add to target kitab
    target_k = db_by_id[target_kitab]
    # Find a bob with matching canon_bab_id
    placed = False
    for bo in target_k['boblar']:
        if bo.get('canon_bab_id') == target_canon_bab:
            bo['hadislar'].append(h)
            bo['hadislar'].sort(key=lambda hh: float(hh['id']) if isinstance(hh.get('id'), (int, float)) else 9999)
            placed = True
            break
    if not placed:
        # Find bob by hadis range
        best_bob = None
        for bo in target_k['boblar']:
            if not bo.get('hadislar'):
                continue
            h_ids = [int(hh['id']) for hh in bo['hadislar'] if isinstance(hh.get('id'), (int, float))]
            if h_ids and min(h_ids) <= hid <= max(h_ids):
                best_bob = bo
                break
        if best_bob is None:
            # Pick last bob with hadis
            for bo in reversed(target_k['boblar']):
                if bo.get('hadislar'):
                    best_bob = bo
                    break
        if best_bob is not None:
            best_bob['hadislar'].append(h)
            best_bob['hadislar'].sort(key=lambda hh: float(hh['id']) if isinstance(hh.get('id'), (int, float)) else 9999)
            placed = True
    if placed:
        moved_strays += 1
        print(f'  Moved #{hid}: UZ-k{kid}.b{bid} -> UZ-k{target_kitab}')

print(f'Moved strays: {moved_strays}')

# Save
with open(DATA, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, separators=(',', ':'))

# Final stats
new_count = sum(len(bo['hadislar']) for k in db for bo in k['boblar'])
unique_ids = set()
for k in db:
    for bo in k['boblar']:
        for h in bo['hadislar']:
            unique_ids.add(h['id'])
print(f'\nFinal: {new_count} hadis entries, {len(unique_ids)} unique IDs')
print(f'data.json: {os.path.getsize(DATA)} bytes')
