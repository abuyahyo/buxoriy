# -*- coding: utf-8 -*-
"""canon.json — UZ data.json ni Abdulboqiy 1-7563 standartiga bog'lovchi mapping.

UZ tarjima allaqachon kanonik raqamlashni ishlatadi (data.json'da hadis.id =
1..7563 oralig'i, lekin gaps va duplicates bor). UZ kitablar 1..98 — kanonik
97 dan farqli (86 ikkiga bo'lingan). Bu skript:

  1. Har UZ kitab → kanonik AR kitab mapping (uz_id → canon_id + arabcha nomi)
  2. Har UZ hadis ID ni kanonik raqamiga bog'lash (asosan 1:1, gaps va duplicate
     lar alohida ro'yxat sifatida)
  3. Tahrir uchun foydali ma'lumot: gaps, duplicates, kitab-spans (UI ga
     qo'shilmaydi, alohida data_issues.json fayliga yoziladi)

Chiqish:
  canon.json       — kichik mapping fayli, UI tomonidan ishlatilishi mumkin
  data_issues.json — to'liq diagnostika (gitignore'da, tahrirlovchi uchun)
"""
import json, os, sys, io
from collections import Counter, defaultdict

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT, 'data.json'), 'r', encoding='utf-8') as f:
    db = json.load(f)
with open(os.path.join(ROOT, 'ar_source.json'), 'r', encoding='utf-8') as f:
    arsrc = json.load(f)
with open(os.path.join(ROOT, 'ar_kitab_titles.json'), 'r', encoding='utf-8') as f:
    titles = json.load(f)

# Canonical AR kitab titles (Arabic + transliteration)
ar_titles = {c['id']: c['arabic'] for c in titles['chapters']}
ar_titles_eng = {c['id']: c['english'] for c in titles['chapters']}

# Canonical AR book ranges (from section_details)
sd = arsrc['metadata']['section_details']
num_to_book = {}
book_range = {}
for bk in range(1, 98):
    info = sd[str(bk)]
    lo, hi = info['hadithnumber_first'], info['hadithnumber_last']
    book_range[bk] = (lo, hi)
    for n in range(lo, hi + 1):
        num_to_book[n] = bk

# Build canonical Arabic text lookup by canonical hadithnumber
ar_text = {}
for h in arsrc['hadiths']:
    n = h['hadithnumber']
    if isinstance(n, float) and n.is_integer():
        n = int(n)
    if isinstance(n, int):
        ar_text[n] = h.get('text', '').strip()

# 1. Per-UZ-kitab → canonical mapping
# We determine canonical kitab by the majority of UZ kitab's hadis IDs:
# which AR book do they fall into?
canon_kitabs = []
for k in db:
    counts = Counter()
    for bo in k['boblar']:
        for h in bo['hadislar']:
            cb = num_to_book.get(int(h['id']))
            if cb:
                counts[cb] += 1
    if not counts:
        continue
    main_canon, main_n = counts.most_common(1)[0]
    total = sum(counts.values())
    entry = {
        'uz_id': k['id'],
        'uz_nomi': k['nomi'],
        'canon_id': main_canon,
        'canon_nomi_ar': ar_titles.get(main_canon, ''),
        'canon_nomi_en': ar_titles_eng.get(main_canon, ''),
    }
    if main_n < total:
        entry['strays'] = {bk: cnt for bk, cnt in counts.items() if bk != main_canon}
    canon_kitabs.append(entry)

# Detect grouping: which UZ kitabs share the same canonical id?
canon_to_uz = defaultdict(list)
for c in canon_kitabs:
    canon_to_uz[c['canon_id']].append(c['uz_id'])
for c in canon_kitabs:
    siblings = [u for u in canon_to_uz[c['canon_id']] if u != c['uz_id']]
    if siblings:
        c['canon_note'] = f'UZ-{c["uz_id"]} sharta canonical kitab {c["canon_id"]} dan iborat (UZ-{",".join(map(str,siblings))} bilan birga)'

# 2. Hadis ID identity check (UZ id == canonical id for almost all)
# We just verify and record any anomalies (none expected — all UZ IDs are in AR canonical)
uz_id_seen = set()
hadis_anom = []
for k in db:
    for bo in k['boblar']:
        for h in bo['hadislar']:
            hid = h['id']
            if hid not in ar_text:
                hadis_anom.append({'uz_id': hid, 'reason': 'not in canonical 1-7563'})
            uz_id_seen.add(hid)

# 3. Duplicates: same UZ id appears in multiple (kitab, bob) locations
uz_loc = defaultdict(list)
for k in db:
    for bo in k['boblar']:
        for h in bo['hadislar']:
            uz_loc[h['id']].append((k['id'], bo['id']))
duplicates = []
for hid, locs in sorted(uz_loc.items()):
    if len(locs) > 1:
        duplicates.append({
            'hid': hid,
            'locations': [{'k': k, 'b': b} for k, b in locs],
            'canon_kitab': num_to_book.get(int(hid)),
        })

# 4. Gaps: canonical IDs missing in UZ data.json
gaps = []
for n in range(1, 7564):
    if n not in uz_loc:
        gaps.append({
            'canon_id': n,
            'canon_kitab': num_to_book.get(n),
            'ar_text_preview': ar_text.get(n, '')[:200],
        })

# 5. Cross-kitab strays: UZ hadis placed in UZ kitab that doesn't match its canonical book
strays = []
canon_uz_map = {c['uz_id']: c['canon_id'] for c in canon_kitabs}
for k in db:
    canon_for_uz_kitab = canon_uz_map.get(k['id'])
    for bo in k['boblar']:
        for h in bo['hadislar']:
            cb = num_to_book.get(int(h['id']))
            if cb and canon_for_uz_kitab and cb != canon_for_uz_kitab:
                strays.append({
                    'hid': h['id'],
                    'uz_loc': {'k': k['id'], 'b': bo['id'], 'k_nomi': k['nomi']},
                    'uz_canon_kitab': canon_for_uz_kitab,
                    'actual_canon_kitab': cb,
                    'ar_text_preview': ar_text.get(int(h['id']), '')[:200],
                })

# --- Write canon.json (compact, UI-usable) ---
canon = {
    'meta': {
        'description': 'Mapping UZ data.json → canonical Abdulboqiy 1-7563 / 97 kitabs',
        'uz_kitabs': len(canon_kitabs),
        'canon_kitabs': 97,
        'uz_hadis_entries': sum(len(v) for v in uz_loc.values()),
        'uz_hadis_unique': len(uz_loc),
        'canon_hadis': 7563,
        'duplicates': len(duplicates),
        'gaps': len(gaps),
        'strays': len(strays),
    },
    'kitabs': canon_kitabs,
}

with open(os.path.join(ROOT, 'canon.json'), 'w', encoding='utf-8') as f:
    json.dump(canon, f, ensure_ascii=False, separators=(',', ':'))
print(f'Wrote canon.json ({os.path.getsize(os.path.join(ROOT, "canon.json"))} bytes)')

# --- Write data_issues.json (for editor review, not for UI) ---
issues = {
    'meta': canon['meta'],
    'duplicates': duplicates,
    'gaps': gaps,
    'strays': strays,
    'hadis_anomalies': hadis_anom,
}
with open(os.path.join(ROOT, 'data_issues.json'), 'w', encoding='utf-8') as f:
    json.dump(issues, f, ensure_ascii=False, indent=2)
print(f'Wrote data_issues.json ({os.path.getsize(os.path.join(ROOT, "data_issues.json"))} bytes)')

# --- Summary ---
print('\n=== STATISTIKA ===')
print(f'UZ kitabs:          {len(canon_kitabs)}')
print(f'Canonical kitabs:   97')
print(f'UZ hadis entries:   {sum(len(v) for v in uz_loc.values())}')
print(f'UZ unique hadis:    {len(uz_loc)}')
print(f'Canonical hadis:    7563')
print(f'Duplicates:         {len(duplicates)}')
print(f'Gaps (missing):     {len(gaps)}')
print(f'Strays (xato kitabda): {len(strays)}')
print()
print('UZ kitab → kanonik AR kitab (juftliklar):')
for c in canon_kitabs:
    note = ''
    if c['uz_id'] != c['canon_id']:
        note = f'  ← farq! UZ {c["uz_id"]} → canon {c["canon_id"]} ({c["canon_nomi_ar"]})'
    if 'canon_note' in c:
        note += '  [' + c['canon_note'] + ']'
    if note:
        print(f'  UZ-{c["uz_id"]:>2} {c["uz_nomi"][:40]:<40} {note}')
