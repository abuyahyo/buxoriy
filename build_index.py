"""Build lightweight index.json + inline books data into index.html.

index.json: book + chapter metadata (no hadith content). Used for book and
chapter page rendering after the user navigates beyond home.

books-data in index.html: tiny JSON (~7 KB) embedded directly in the HTML
so the home page renders instantly without any network fetch.
"""
import json
import re

with open('data.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

# --- index.json: book + chapter metadata (no hadis content) ---
idx = []
for k in db:
    book = {'id': k['id'], 'nomi': k['nomi'], 'boblar': []}
    for b in k['boblar']:
        bob = {
            'id': b['id'],
            'nomi': b.get('nomi', ''),
            'hC': len(b.get('hadislar', [])),
        }
        if b.get('izoh'):
            bob['izoh'] = b['izoh']
        if b.get('muallaqot'):
            bob['muallaqot'] = b['muallaqot']
        book['boblar'].append(bob)
    idx.append(book)

with open('index.json', 'w', encoding='utf-8') as f:
    json.dump(idx, f, ensure_ascii=False, separators=(',', ':'))

# --- BOOKS data: home page (id, nomi, bob count, hadis count) ---
home = []
for k in db:
    home.append({
        'id': k['id'],
        'nomi': k['nomi'],
        'bC': len(k['boblar']),
        'hC': sum(len(b.get('hadislar', [])) for b in k['boblar']),
    })
home_json = json.dumps(home, ensure_ascii=False, separators=(',', ':'))

# Inject into index.html between markers
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

pattern = r'(<script type="application/json" id="books-data">).*?(</script>)'
new_html, count = re.subn(pattern, lambda m: m.group(1) + home_json + m.group(2), html, flags=re.DOTALL)
if count != 1:
    raise SystemExit(f'ERROR: books-data marker not found exactly once in index.html (found {count})')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

# Bump sw.js cache version so browsers see a new SW and trigger the
# "Update available" flow. Use data.json mtime as a stable build id.
import os
sw_path = 'sw.js'
if os.path.exists(sw_path):
    build_id = int(os.path.getmtime('data.json'))
    with open(sw_path, 'r', encoding='utf-8') as f:
        sw = f.read()
    sw_new, n = re.subn(r"const CACHE = '[^']*';", f"const CACHE = 'buxoriy-v{build_id}';", sw, count=1)
    if n == 1 and sw_new != sw:
        with open(sw_path, 'w', encoding='utf-8') as f:
            f.write(sw_new)
        print(f'sw.js: CACHE → buxoriy-v{build_id}')

print(f'data.json:    {os.path.getsize("data.json"):>10,} bytes ({os.path.getsize("data.json")/1024/1024:.2f} MB)')
print(f'index.json:   {os.path.getsize("index.json"):>10,} bytes ({os.path.getsize("index.json")/1024:.1f} KB)')
print(f'BOOKS inline: {len(home_json):>10,} bytes ({len(home_json)/1024:.1f} KB)')
print(f'index.html:   {os.path.getsize("index.html"):>10,} bytes ({os.path.getsize("index.html")/1024:.1f} KB)')
