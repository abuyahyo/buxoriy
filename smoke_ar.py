"""Smoke test the /ar/ page: fetch HTML + index.json + a slice of data.json and
verify basic invariants."""
import json, urllib.request, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = 'http://localhost:8765'

def get_text(path):
    return urllib.request.urlopen(BASE + path).read().decode('utf-8')

def get_json(path):
    return json.loads(get_text(path))

# 1. ar/index.html — check inline BOOKS + UI markers + RTL
html = get_text('/ar/')
assert 'id="books-data"' in html, 'books-data script tag missing'
assert 'dir="rtl"' in html, 'RTL missing'
assert 'صحيح البخاري' in html, 'Title in Arabic missing'
assert 'كتاب التوحيد' in html, 'Last kitab name missing from inline'
assert 'ابحث في الأحاديث' in html, 'Search placeholder missing'
assert 'kitobGrid' in html, 'Kitob grid container missing'
print('OK ar/index.html: RTL, Arabic title, inline 97 kitabs present')

# 2. ar/index.json
idx = get_json('/ar/index.json')
assert len(idx) == 97, f'index.json has {len(idx)} kitabs, expected 97'
assert idx[0]['nomi'] == 'كتاب بدء الوحى', f'first kitab name: {idx[0]["nomi"]}'
assert idx[-1]['nomi'] == 'كتاب التوحيد', f'last kitab name: {idx[-1]["nomi"]}'
total_h = sum(k['hC'] for k in idx)
print(f'OK ar/index.json: 97 kitabs, {total_h} total hadiths')

# 3. ar/data.json — sample first kitab
data = get_json('/ar/data.json')
assert len(data) == 97
k1 = data[0]
assert k1['id'] == 1
assert len(k1['hadislar']) == 7, f'kitab 1 has {len(k1["hadislar"])} hadiths'
h1 = k1['hadislar'][0]
assert h1['id'] == 1
import re as _re
stripped = _re.sub(r'[ً-ٰٟـ]', '', h1['matn'])
assert 'إنما الأعمال بالنيات' in stripped, f'hadith 1 famous phrase missing in stripped text: {stripped[:200]}'
print(f'OK ar/data.json: hadith #1 matn starts with: {h1["matn"][:80]}...')

# 4. main index.html: Arabic link present
main = get_text('/')
assert 'ar-link' in main, '.ar-link CSS class missing'
assert 'href="ar/"' in main, 'link to ar/ missing'
assert 'العربية' in main, 'Arabic label missing on main page'
print('OK main /: العربية link present')

# 5. ar/sw.js + ar/manifest.json
sw = get_text('/ar/sw.js')
assert 'buxoriy-ar-v' in sw, 'sw cache name missing'
mf = get_json('/ar/manifest.json')
assert mf['lang'] == 'ar' and mf['dir'] == 'rtl'
print('OK ar/sw.js + manifest.json')

print('\nALL CHECKS PASSED')
