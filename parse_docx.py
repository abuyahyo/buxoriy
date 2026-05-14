"""Parse Sahih Bukhari .docx files into JSON structure matching data.json schema.

Notes:
- .docx files use global canonical hadith numbers (e.g., Иймон: 8-58).
- Chapter headers contain "БОБ" word OR are in all-caps Cyrillic.
- Hadith starts: "\\d+\\.\\s+Name..." (mixed case, not chapter).
- muallaqot: text between chapter header and first hadith in that chapter.
- Footnotes marked with "*" go to izoh field at the end.
"""
import zipfile, re, sys, json, os

CYR_LOW = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяғҳқўіїәө')

def extract_paras(path):
    with zipfile.ZipFile(path) as z:
        with z.open('word/document.xml') as f:
            xml = f.read().decode('utf-8')
    paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.DOTALL)
    out = []
    for p in paras:
        t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
        t = (t.replace('&quot;', '"').replace('&amp;', '&')
              .replace('&apos;', "'").replace('&lt;', '<').replace('&gt;', '>'))
        # Normalize unicode dashes & weird spaces
        t = t.replace('­', '').replace('​', '')
        t = t.strip()
        if t:
            out.append(t)
    return out

def has_lower_cyr(s):
    return any(c in CYR_LOW for c in s)

def is_chapter(p):
    # Marker word
    if re.search(r'\b[Бб][Оо][Бб][Ии]?\b', p[:300]):
        return True
    # All-caps Cyrillic (no lowercase) and contains Cyrillic
    if any(c.upper() in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯҒҲҚЎ' for c in p):
        if not has_lower_cyr(p):
            return True
    return False

HADIS_RE = re.compile(r'^(\d+)\s*[.‐‒–—―\-]\s+(.*)', re.DOTALL)

HADITH_MARKERS = (
    'розияллоҳу', 'раҳматуллоҳи', 'разияллоҳу', 'раҳимаҳуллоҳ',
    'ривоят қилинади', 'ривоят қилади', 'ривоят қиладилар',
    'айтади', 'айтган', 'айтди', 'айтиб', 'айтилади',
    'деди', 'дейди', 'дейилади', 'дедилар',
    'келтирган', 'нақл қилган', 'нақл қиладилар',
    'набий соллаллоҳу', 'расулуллоҳ соллаллоҳу',
)

def parse_hadis_start(p):
    m = HADIS_RE.match(p)
    if not m: return None
    if is_chapter(p): return None
    sample = p[:400].lower()
    if not any(mk in sample for mk in HADITH_MARKERS):
        return None
    n = int(m.group(1))
    rest = m.group(2)
    return n, rest

def extract_chapter_num(p):
    m = re.match(r'^(\d+)\s*[­\-–.]\s*[Бб][Оо][Бб]', p)
    if m: return int(m.group(1))
    return None

NARRATOR_TAIL_RE = re.compile(
    r'^(.+?(?:розияллоҳу\s+(?:анҳунн[аи]|анҳумо|анҳума|анҳо|анҳу)'
    r'|раҳматуллоҳи\s+\S+|разияллоҳу\s+\S+'
    r'|раҳимаҳуллоҳ\S*))'
)
VERB_TAIL_RE = re.compile(
    r'^(.+?)\s+(?:ривоят\s+қилинади|айтади|айтган|айтди|деди|дейди|шундай\s+деган|шундай\s+деди)\s*$'
)

def extract_rowi_matn(lines):
    if not lines: return '', ''
    first = lines[0].strip()
    rest_lines = lines[1:]
    if first.endswith(':'):
        intro = first[:-1].strip()
        m = NARRATOR_TAIL_RE.match(intro)
        if m:
            rowi = m.group(1).strip()
        else:
            m2 = VERB_TAIL_RE.match(intro)
            if m2:
                rowi = m2.group(1).strip()
            else:
                rowi = intro
        matn = '\n\n'.join(rest_lines).strip()
    else:
        rowi = ''
        matn = '\n\n'.join(lines).strip()
    return rowi, matn

def parse_docx(path):
    paras = extract_paras(path)
    if not paras: return []
    body = paras[1:]  # skip book title
    chapters = []
    cur_chap = None
    pending = []  # paragraphs accumulated since last hadith/chapter (= muallaqot or hadith continuation)
    cur_hadis = None
    cur_hadis_lines = []

    def close_hadis():
        nonlocal cur_hadis, cur_hadis_lines
        if cur_hadis is None: return
        h_num = cur_hadis
        rowi, matn = extract_rowi_matn(cur_hadis_lines)
        h = {'id': h_num, 'matn': matn, 'rowi': rowi}
        izoh_match = re.search(r'\n\*?\s*Изоҳ\s*:\s*(.+)$', matn, re.DOTALL)
        if izoh_match:
            izoh_text = izoh_match.group(1).strip()
            matn = matn[:izoh_match.start()].rstrip()
            h['izoh'] = izoh_text
            h['matn'] = matn
        cur_chap['hadislar'].append(h)
        cur_hadis = None
        cur_hadis_lines = []

    def close_chap():
        nonlocal cur_chap, pending
        if cur_chap is None: return
        # If pending exists and no hadiths started, it's the muallaqot
        if pending and not cur_chap['hadislar']:
            cur_chap['muallaqot'] = '\n\n'.join(pending).strip()
        elif pending:
            # Stuff after last hadith - rare. Append to last hadith matn.
            if cur_chap['hadislar']:
                cur_chap['hadislar'][-1]['matn'] += '\n\n' + '\n\n'.join(pending)
        pending = []
        if not cur_chap.get('muallaqot'):
            cur_chap.pop('muallaqot', None)
        chapters.append(cur_chap)
        cur_chap = None

    chap_id = 0
    for p in body:
        # Try hadith first (more specific)
        ph = parse_hadis_start(p)
        if ph is not None:
            n, rest = ph
            # close previous hadith
            close_hadis()
            # if no current chapter yet, create one
            if cur_chap is None:
                chap_id += 1
                cur_chap = {'id': chap_id, 'nomi': '', 'hadislar': []}
            # before starting hadith, if we have pending paragraphs and no hadiths yet → muallaqot
            if pending and not cur_chap['hadislar']:
                cur_chap['muallaqot'] = '\n\n'.join(pending).strip()
                pending = []
            elif pending and cur_chap['hadislar']:
                # pending content between hadiths — append to previous hadith
                cur_chap['hadislar'][-1]['matn'] += '\n\n' + '\n\n'.join(pending)
                pending = []
            cur_hadis = n
            cur_hadis_lines = [rest]  # store the rest (after "N. ")
            continue
        if is_chapter(p):
            # close previous hadith and chapter
            close_hadis()
            close_chap()
            chap_id += 1
            cur_chap = {'id': chap_id, 'nomi': p, 'hadislar': []}
            pending = []
            continue
        # normal text
        if cur_hadis is not None:
            cur_hadis_lines.append(p)
        else:
            pending.append(p)
    # finalize
    close_hadis()
    close_chap()
    return chapters

if __name__ == '__main__':
    fn = sys.argv[1]
    chapters = parse_docx(f'buxoriy kitoblari/{fn}')
    print(json.dumps(chapters, ensure_ascii=False, indent=2))
