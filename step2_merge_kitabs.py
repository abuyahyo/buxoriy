# -*- coding: utf-8 -*-
"""Step 2: Merge UZ-86 + UZ-87 into single canonical kitab 86; shift UZ-88..98 → 87..97.

Result: 98 kitabs → 97 kitabs, matching canonical structure.

URL redirects handled in index.html JS (separate edit).

Reversible: --revert restores from data.json.bak3.
"""
import json, os, sys, io, shutil, argparse

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data.json')
BACKUP = os.path.join(ROOT, 'data.json.bak3')

ap = argparse.ArgumentParser()
ap.add_argument('--revert', action='store_true')
args = ap.parse_args()

if args.revert:
    if not os.path.exists(BACKUP):
        print('No backup to revert from')
        sys.exit(1)
    shutil.copy(BACKUP, DATA)
    print('Reverted from backup')
    sys.exit(0)

shutil.copy(DATA, BACKUP)
print(f'Backup: {BACKUP}')

with open(DATA, 'r', encoding='utf-8') as f:
    db = json.load(f)

# Find kitabs
k86 = next(k for k in db if k['id'] == 86)
k87 = next(k for k in db if k['id'] == 87)

print(f'Before merge:')
print(f'  UZ-86 "{k86["nomi"]}" — {len(k86["boblar"])} bob')
print(f'  UZ-87 "{k87["nomi"][:50]}..." — {len(k87["boblar"])} bob')

# Renumber UZ-87's boblar starting from (last UZ-86 bob id + 1)
offset = max(b['id'] for b in k86['boblar'])
print(f'UZ-87 boblari ID siljishi: +{offset}')
for b in k87['boblar']:
    b['id'] += offset

# Append UZ-87 boblar into UZ-86
k86['boblar'].extend(k87['boblar'])

# Update UZ-86 name to reflect merge (keep Uzbek but mark it as canonical)
# Original: "Ҳаддлар китоби"
# Keep this — canonical_nomi_ar already in canon_nomi_ar field
# UZ-86 canon_kitab = 86, canon_nomi_ar = "كتاب الحدود" (already set)

print(f'After merge UZ-86: {len(k86["boblar"])} bob, {sum(len(b.get("hadislar",[])) for b in k86["boblar"])} hadis')

# Remove UZ-87 from db
db = [k for k in db if k['id'] != 87]

# Shift UZ-88..98 down to 87..97
shifted = 0
for k in db:
    if k['id'] >= 88:
        k['id'] -= 1
        shifted += 1
print(f'Shifted {shifted} kitab IDs (88..98 → 87..97)')

# Save
with open(DATA, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, separators=(',', ':'))

# Verify
print(f'\nFinal: {len(db)} kitabs')
for k in db:
    if k['id'] >= 85:
        print(f'  UZ-{k["id"]} ({k.get("canon_kitab","?")}) "{k["nomi"][:45]}" — '
              f'{len(k["boblar"])} bob, '
              f'{sum(len(b.get("hadislar",[])) for b in k["boblar"])} hadis')

print(f'\ndata.json: {os.path.getsize(DATA)} bytes')
print(f'\nNext: add hash redirect logic to index.html so old #k/87/* and #k/8N/* URLs still work')
