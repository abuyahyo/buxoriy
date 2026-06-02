"""crossrefs.json ni sahihul-buxoriy.txt ichida yozilgan atraf havolalaridan
chiqarib olish.

Manbada hadis matnlarida va izohlarda "X-ҳадис", "X-ҳадисга қаранг",
"X ва Y-ҳадислар" kabi shaklda parallel hadislarga raqamli havolalar bor.
Bu ma'lumot Hilol Nashr nashrida muharrirlar tomonidan qo'shilgan — lekin
manba sahihul-buxoriy.txt repository ichida mavjud va user bizning loyihaga
qo'shgan, shuning uchun shu manbadan o'qib strukturalashtiramiz.

Natija crossrefs.json: {hadis_id: [parallel_id, ...]}
"""
import re
import json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).parent
SRC = REPO / 'sahihul-buxoriy.txt'
DATA = REPO / 'data.json'
OUT = REPO / 'crossrefs.json'

re_kitob = re.compile(r'^(\d+)-KITOB:')
re_hadis = re.compile(r'^\[Hadis\s+([\d,\s]+?)(?:\s*\([^)]*\))?\.?\]\s*$')

# Hadis raqamiga havola variantlari:
#   "298-ҳадис", "298-ҳадисга", "298-ҳадиснинг", "298-ҳадислар"
#   "405, 417-ҳадисларга" — range bilan
#   "298, 299-ҳадислар"
# Strategiya: "X-ҳадис" ni topib, undan oldingi tinish belgilari orqali keluvchi
# raqamlarni ham qo'shamiz ("X, Y-ҳадис" → [X, Y])
re_ref_block = re.compile(r'((?:\d{1,4}\s*,\s*)*\d{1,4})\s*-\s*[ҳҲ]адис')

text = SRC.read_text(encoding='utf-8')

# Hadis chegaralarini topish: har hadis blokining boshi va oxiri
hadis_blocks = {}  # id -> (start, end)
cur_id = None
cur_start = None
started = False
lines = text.split('\n')
line_starts = [0]
for ln in lines[:-1]:
    line_starts.append(line_starts[-1] + len(ln) + 1)

for idx, ln in enumerate(lines):
    if ln.strip() == 'ILOVALAR':
        if cur_id is not None:
            hadis_blocks[cur_id] = (cur_start, line_starts[idx])
        break
    if re_kitob.match(ln):
        started = True
    if not started:
        continue
    mh = re_hadis.match(ln)
    if mh:
        if cur_id is not None:
            hadis_blocks[cur_id] = (cur_start, line_starts[idx])
        cur_id = int(re.findall(r'\d+', mh.group(1))[0])
        cur_start = line_starts[idx + 1] if idx + 1 < len(lines) else line_starts[idx]

if cur_id is not None and cur_id not in hadis_blocks:
    hadis_blocks[cur_id] = (cur_start, len(text))

print(f"Hadis bloklari: {len(hadis_blocks)}")

# Har bir blok ichida atraf havolalarini topish
crossrefs = defaultdict(set)
for hid, (s, e) in hadis_blocks.items():
    body = text[s:e]
    for m in re_ref_block.finditer(body):
        # m.group(1) — "405, 417" yoki "298" yoki "1, 2, 3"
        nums = re.findall(r'\d{1,4}', m.group(1))
        for ns in nums:
            ref_id = int(ns)
            if ref_id == hid or ref_id < 1 or ref_id > 7563:
                continue
            crossrefs[hid].add(ref_id)

# Simmetrik yopish: agar A→B yozilgan bo'lsa, B→A ham (parallellik)
sym = defaultdict(set)
for a, refs in crossrefs.items():
    for b in refs:
        sym[a].add(b)
        sym[b].add(a)

# data.json'dagi mavjud id'lar bilan kesishish
db = json.load(open(DATA, encoding='utf-8'))
valid_ids = set()
for k in db:
    for b in k['boblar']:
        for h in b['hadislar']:
            valid_ids.add(h['id'])

result = {}
for oid, refs in sym.items():
    if oid not in valid_ids:
        continue
    filtered = sorted(r for r in refs if r in valid_ids and r != oid)
    if filtered:
        result[oid] = filtered

# JSON yozish
out = {str(k): v for k, v in sorted(result.items())}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

total_pairs = sum(len(v) for v in result.values()) // 2
print(f"\nCross-refs natija (manbadan ajratilgan):")
print(f"  Cross-ref'li hadis: {len(result)} / {len(valid_ids)} ({100*len(result)/len(valid_ids):.1f}%)")
print(f"  Jami juftliklar: {total_pairs:,}")
if result:
    print(f"  O'rtacha ref soni: {sum(len(v) for v in result.values()) / len(result):.1f}")
    print(f"  Maks ref soni: {max(len(v) for v in result.values())}")
print(f"  Fayl: {OUT.name} ({OUT.stat().st_size:,} bayt)")
