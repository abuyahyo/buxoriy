# -*- coding: utf-8 -*-
"""Phase 1: Augment data.json with canonical metadata.

Pure additive: no structural changes, no hadis/bob/kitab removed or moved.
Just adds these fields:

  Per-kitab:    canon_kitab (int 1-97), canon_nomi_ar (string)
  Per-bob:      canon_bab_id (int|float|null), canon_bab_nomi_ar (string|null)
                — derived from the dominant canonical bab of the bob's hadiths
  Per-hadis:    canon_no (int|float) — same as id for almost all; if a UZ hadis
                somehow has a non-canonical id, canon_no still points to canonical

Reversible: just re-run build_data.py to drop these fields, OR run with --revert.

Outputs:
  data.json (modified in place — backup created at data.json.bak)
"""
import json, os, sys, io, sqlite3, shutil, argparse
from collections import Counter

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data.json')
BACKUP = os.path.join(ROOT, 'data.json.bak')
CANON = os.path.join(ROOT, 'canon.json')

ap = argparse.ArgumentParser()
ap.add_argument('--revert', action='store_true', help='Strip canon_* fields')
args = ap.parse_args()

# Load
with open(DATA, 'r', encoding='utf-8') as f:
    db = json.load(f)
with open(CANON, 'r', encoding='utf-8') as f:
    canon = json.load(f)

if args.revert:
    print('Reverting: stripping canon_* fields from data.json')
    n_k = n_b = n_h = 0
    for k in db:
        for fld in ('canon_kitab', 'canon_nomi_ar'):
            if fld in k:
                del k[fld]
                n_k += 1
        for bo in k.get('boblar', []):
            for fld in ('canon_bab_id', 'canon_bab_nomi_ar'):
                if fld in bo:
                    del bo[fld]
                    n_b += 1
            for h in bo.get('hadislar', []):
                if 'canon_no' in h:
                    del h['canon_no']
                    n_h += 1
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Stripped: {n_k} kitab fields, {n_b} bob fields, {n_h} hadis fields')
    sys.exit(0)

# Backup
shutil.copy(DATA, BACKUP)
print(f'Backed up data.json → data.json.bak ({os.path.getsize(BACKUP)} bytes)')

# 1. Kitab → canon mapping (already in canon.json)
uz_to_canon = {k['uz_id']: (k['canon_id'], k['canon_nomi_ar']) for k in canon['kitabs']}

# 2. Hadis → canon bab (from Islamic-OS DB)
con = sqlite3.connect(os.path.join(ROOT, 'bukhari_qitab.db'))
cur = con.cursor()
h_to_bab = {}    # canonical hadis_no -> (bookNumber, babID, arabicBabName)
for r in cur.execute("""
    SELECT CAST(hadithNumber AS REAL), bookNumber, babID, arabicBabName
    FROM bukhari
    WHERE hadithNumber IS NOT NULL AND hadithNumber != ''
"""):
    h_to_bab[r[0]] = (int(r[1]), r[2], (r[3] or '').strip())
con.close()

print(f'Loaded {len(h_to_bab)} hadis → canonical (book, bab) mappings')

# 3. Process each kitab/bob/hadis
n_kitab = n_bob = n_hadis = 0
bob_with_canon = bob_no_canon = 0
hadis_with_canon = hadis_no_canon = 0

for k in db:
    canon_kid, canon_kname = uz_to_canon.get(k['id'], (None, None))
    if canon_kid:
        k['canon_kitab'] = canon_kid
        k['canon_nomi_ar'] = canon_kname
        n_kitab += 1
    for bo in k.get('boblar', []):
        # Determine dominant canonical bab among this bob's hadis
        bab_counter = Counter()
        bab_names = {}
        for h in bo.get('hadislar', []):
            hid = h['id']
            hid_f = float(hid)
            info = h_to_bab.get(hid_f)
            if info:
                _, babid, babname = info
                bab_counter[babid] += 1
                bab_names[babid] = babname
                h['canon_no'] = int(hid) if isinstance(hid, int) or (isinstance(hid, float) and hid.is_integer()) else hid
                hadis_with_canon += 1
            else:
                hadis_no_canon += 1
            n_hadis += 1
        # Most common bab
        if bab_counter:
            top_bab, _ = bab_counter.most_common(1)[0]
            bo['canon_bab_id'] = top_bab
            bo['canon_bab_nomi_ar'] = bab_names.get(top_bab, '')
            bob_with_canon += 1
        else:
            bob_no_canon += 1
        n_bob += 1

# Write
with open(DATA, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, separators=(',', ':'))

print(f'\n=== Phase 1 natijasi ===')
print(f'Kitablar canonik bilan: {n_kitab}/{len(db)}')
print(f'Boblar canonik bab bilan: {bob_with_canon}/{n_bob} (yo\'q: {bob_no_canon})')
print(f'Hadislar canonik no bilan: {hadis_with_canon}/{n_hadis} (yo\'q: {hadis_no_canon})')
print(f'data.json yangilandi ({os.path.getsize(DATA)} bytes)')
print(f'Backup: data.json.bak ({os.path.getsize(BACKUP)} bytes)')
print(f'\nQaytarish uchun: python phase1_canon_meta.py --revert')
