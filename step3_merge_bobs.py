# -*- coding: utf-8 -*-
"""Step 3: Merge UZ bobs that share the same canonical bab (4075 -> ~3873).

For each UZ kitab:
  - Group its boblar by canon_bab_id (assigned in Phase 1).
  - If multiple UZ bobs share the same canon_bab_id, merge them:
    titles are joined with " // ", izoh/muallaqot concatenated, hadislar combined and re-sorted.
  - Bobs without canon_bab_id stay as-is (UZ-specific content not in
    canonical structure).
  - After merging, bob ids within each kitab are renumbered sequentially.

Reversible: --revert restores data.json from data.json.bak4.
"""
import json, os, sys, io, shutil, argparse
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data.json')
BACKUP = os.path.join(ROOT, 'data.json.bak4')

ap = argparse.ArgumentParser()
ap.add_argument('--revert', action='store_true')
args = ap.parse_args()

if args.revert:
    if not os.path.exists(BACKUP):
        print('No backup to revert from'); sys.exit(1)
    shutil.copy(BACKUP, DATA)
    print('Reverted')
    sys.exit(0)

shutil.copy(DATA, BACKUP)
print(f'Backup: {BACKUP}')

with open(DATA, 'r', encoding='utf-8') as f:
    db = json.load(f)

bob_count_before = sum(len(k['boblar']) for k in db)
print(f'Before: {bob_count_before} bobs total')

merged_count = 0
for k in db:
    grouped = []
    seen_canon = {}  # canon_bab_id -> idx in grouped
    for bo in k['boblar']:
        cb = bo.get('canon_bab_id')
        if cb is not None and cb in seen_canon:
            target = grouped[seen_canon[cb]]
            # Combine titles only if different
            new_nomi = (bo.get('nomi') or '').strip()
            existing_nomi = (target.get('nomi') or '').strip()
            if new_nomi and new_nomi not in existing_nomi:
                target['nomi'] = existing_nomi + ' // ' + new_nomi
            # Combine izoh
            new_izoh = (bo.get('izoh') or '').strip()
            if new_izoh:
                target['izoh'] = ((target.get('izoh') or '').strip() + '\n\n' + new_izoh).strip()
            # Combine muallaqot
            new_mu = (bo.get('muallaqot') or '').strip()
            if new_mu:
                target['muallaqot'] = ((target.get('muallaqot') or '').strip() + '\n\n' + new_mu).strip()
            # Merge hadislar
            target['hadislar'].extend(bo.get('hadislar', []))
            merged_count += 1
        else:
            grouped.append(bo)
            if cb is not None:
                seen_canon[cb] = len(grouped) - 1
    # Re-sort hadislar and renumber bob ids
    for i, bo in enumerate(grouped):
        hl = bo.get('hadislar', [])
        # Dedupe hadis ids (keep first occurrence — sometimes a hadis was added twice via merge)
        seen_h = set()
        deduped = []
        for h in hl:
            hid_key = (h.get('id'), h.get('tarjima_status') == 'missing')
            if hid_key in seen_h:
                continue
            seen_h.add(hid_key)
            deduped.append(h)
        # Sort by hadis id
        deduped.sort(key=lambda h: float(h['id']) if isinstance(h.get('id'), (int, float)) else 9999)
        bo['hadislar'] = deduped
        bo['id'] = i + 1
    k['boblar'] = grouped

bob_count_after = sum(len(k['boblar']) for k in db)
print(f'After:  {bob_count_after} bobs total (merged {merged_count})')

# Sample: book 65 (Tafsir, biggest change)
k65 = next(k for k in db if k['id'] == 65)
print(f'\nUZ-65 Tafsir: {len(k65["boblar"])} bobs (was 497)')

# Sample: book 2 (Iman)
k2 = next(k for k in db if k['id'] == 2)
print(f'UZ-2 Iman: {len(k2["boblar"])} bobs (was 43)')

with open(DATA, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
print(f'\ndata.json: {os.path.getsize(DATA)} bytes')
