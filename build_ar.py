"""Build ar/data.json and ar/index.json for the Arabic-only /buxoriy/ar/ site.

Sources:
- ar_source.json — fawazahmed0/hadith-api ara-bukhari (canonical 1-7563 numbering)
- ar_kitab_titles.json — AhmedBaset/hadith-json bukhari (Arabic kitab titles for 97 books)

Output:
- ar/data.json — full Arabic hadiths grouped by kitab
- ar/index.json — kitab metadata + hadith counts (no hadith bodies)
"""
import json, os, re, sys, io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'ar_source.json')
TITLES = os.path.join(ROOT, 'ar_kitab_titles.json')
OUT_DIR = os.path.join(ROOT, 'ar')
os.makedirs(OUT_DIR, exist_ok=True)

with open(SRC, 'r', encoding='utf-8') as f:
    src = json.load(f)
with open(TITLES, 'r', encoding='utf-8') as f:
    titles_src = json.load(f)

# Arabic kitab titles: 97 entries, 1-indexed by chapter id
kitab_titles_ar = {c['id']: c['arabic'] for c in titles_src['chapters']}

# Build a hadithnumber -> book lookup from section_details (authoritative,
# because the source's reference.book is broken for 311 entries — they have book=0).
sd = src['metadata']['section_details']
num_to_book = {}
for bk in range(1, 98):
    info = sd[str(bk)]
    lo, hi = info['hadithnumber_first'], info['hadithnumber_last']
    for n in range(lo, hi + 1):
        num_to_book[n] = bk

def book_for(num):
    if isinstance(num, float):
        return num_to_book.get(int(num))
    return num_to_book.get(num)

# Group hadiths by book using the lookup, falling back to reference.book if it's valid
hadiths = src['hadiths']
books = {i: [] for i in range(1, 98)}
empty_count = 0
unassigned_count = 0
for h in hadiths:
    num = h['hadithnumber']
    bk = book_for(num)
    if bk is None:
        ref_bk = h['reference'].get('book')
        if 1 <= ref_bk <= 97:
            bk = ref_bk
        else:
            unassigned_count += 1
            continue
    text = (h.get('text') or '').strip()
    if not text:
        empty_count += 1
        continue
    if isinstance(num, float) and num.is_integer():
        num = int(num)
    books[bk].append({
        'id': num,
        'matn': text,
    })

print(f'Empty-text hadiths skipped: {empty_count}')
print(f'Unassigned hadiths skipped: {unassigned_count}')

# Sort hadiths within each book by id (ints first, then fractional X.2 attaches to its X)
for bk in books:
    books[bk].sort(key=lambda h: (int(h['id']), 0 if isinstance(h['id'], int) else 1))

# Build data.json: list of kitab objects
data = []
total_h = 0
for bk_id in range(1, 98):
    if bk_id not in kitab_titles_ar:
        print(f'WARN: kitab {bk_id} has no Arabic title', file=sys.stderr)
        continue
    hadis_list = books[bk_id]
    total_h += len(hadis_list)
    data.append({
        'id': bk_id,
        'nomi': kitab_titles_ar[bk_id],
        'hadislar': hadis_list,
    })

print(f'Total kitabs: {len(data)}, total hadiths: {total_h}')

# Write data.json (minified)
out_data = os.path.join(OUT_DIR, 'data.json')
with open(out_data, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
print(f'Wrote {out_data} ({os.path.getsize(out_data)} bytes)')

# Build index.json: kitab metadata only (id, nomi, hC=hadith count)
index = [{'id': k['id'], 'nomi': k['nomi'], 'hC': len(k['hadislar'])} for k in data]
out_index = os.path.join(OUT_DIR, 'index.json')
with open(out_index, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, separators=(',', ':'))
print(f'Wrote {out_index} ({os.path.getsize(out_index)} bytes)')

# Inline the index list into ar/index.html so the home page renders instantly.
html_path = os.path.join(OUT_DIR, 'index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()
inline_json = json.dumps(index, ensure_ascii=False, separators=(',', ':'))
pat = re.compile(r'(<script id="books-data" type="application/json">)(.*?)(</script>)', re.S)
new_html, n = pat.subn(lambda m: m.group(1) + inline_json + m.group(3), html, count=1)
if n != 1:
    raise SystemExit('Failed to inject inline BOOKS into ar/index.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)
print(f'Injected {len(inline_json)} chars of inline BOOKS into {html_path}')

# Bump SW CACHE name using data.json mtime
sw_path = os.path.join(OUT_DIR, 'sw.js')
with open(sw_path, 'r', encoding='utf-8') as f:
    sw = f.read()
mt = int(os.path.getmtime(out_data))
new_sw, n = re.subn(r"const CACHE = 'buxoriy-ar-v[^']*';",
                    f"const CACHE = 'buxoriy-ar-v{mt}';",
                    sw, count=1)
if n != 1:
    raise SystemExit('Failed to update sw.js CACHE name')
with open(sw_path, 'w', encoding='utf-8') as f:
    f.write(new_sw)
print(f'Bumped sw.js CACHE to buxoriy-ar-v{mt}')
