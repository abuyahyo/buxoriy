# -*- coding: utf-8 -*-
"""sahihul-buxoriy.txt -> data.json.

Манба матн файлини тузилмали data.json га ўгиради:
  - 97 китоб -> боблар -> ҳадислар
  - арабча матн (оят/иснод) ташланади (фақат ўзбекча)
  - изоҳ-footnote [N] лар матн ичига (...) шаклида киритилади (боб доирасида)
  - ИЛОВАЛАР бўлимидаги тафсилий изоҳлар тегишли ҳадис izoh майдонига қўшилади
  - МУҚАДДИМА ва [Kirish] блоклари ташланади
"""
import json
import re

SRC = 'sahihul-buxoriy.txt'
OUT = 'data.json'

EQ = '=' * 80
DASH = '-' * 80

re_kitob = re.compile(r'^(\d+)-KITOB:\s*(.*)$')
re_bob = re.compile(r'^(\d+)\.(\d+)-BOB:\s*(.*)$')
# бир блокда бир неча рақам ёки "(такрорий)" изоҳи бўлиши мумкин
re_hadis = re.compile(r'^\[Hadis\s+([\d,\s]+?)(?:\s*\([^)]*\))?\.?\]\s*$')
re_fn_def = re.compile(r'^\[(\d+)\]\s+(.+)$')          # footnote таърифи
re_bob_prefix = re.compile(r'^\s*\d+\s*-\s*[Бб][Оо][Бб]\s*\.?\s*')  # "N-боб." олд қўшимча

# арабча белгилар диапазони (Arabic + Arabic Presentation Forms)
AR = re.compile(r'[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]')

PROPER = {'макка': 'Макка', 'мадина': 'Мадина', 'аллоҳ': 'Аллоҳ',
          'қуръон': 'Қуръон', 'муҳаммад': 'Муҳаммад'}


def is_arabic_line(s):
    s2 = s.replace(' ', '')
    if not s2:
        return False
    ar = len(AR.findall(s2))
    return ar / len(s2) > 0.4


def kitob_name(raw):
    # "1. ВАҲИЙНИНГ БОШЛАНИШИ КИТОБИ" -> "Ваҳийнинг бошланиши китоби"
    name = re.sub(r'^\s*\d+\.\s*', '', raw).strip()
    name = re.sub(r'\s+', ' ', name)
    cap = name.capitalize()
    for low, hi in PROPER.items():
        cap = re.sub(r'(?<![а-яёҳқғўъ])' + low + r'(?![а-яёҳқғўъ])', hi, cap)
    return cap


_ARCLS = '؀-ۿﭐ-﷿ﹰ-﻿﴾﴿'
# арабча блокни ёнидаги тиниш белгилари/бўшлиқлари билан бирга (улар орфан
# бўлиб қолмаслиги учун). Эллипсис «...» бузилмайди — фақат арабча атрофида.
_AR_BLOB = re.compile(r'[\s.:;،؛]*[' + _ARCLS + r'][\s.:;،؛' + _ARCLS + r']*')


def strip_arabic(text):
    text = _AR_BLOB.sub(' ', text)
    text = re.sub(r'«\s*»', '', text)             # бўшаб қолган тирноқлар
    text = re.sub(r'\(\s*\)', '', text)           # бўшаб қолган қавслар
    return text


# OCR аралашма токенларини тузатиш (лотин↔кирилл look-alike). Кириллча бўлиши
# керак сўзларда лотин ҳарфлар, илмий ном/ношир номида кирилл ҳарфлар аралашган.
OCR_FIXES = {
    'Mаккада': 'Маккада', 'Mаккага': 'Маккага', 'Cарфлагани': 'Сарфлагани',
    'Аltаf': 'Altaf', 'sоns': 'sons', 'mеdicа': 'medica',
    'cоlоcуnthis': 'colocynthis', 'cоlоcynthis': 'colocynthis',
    'urоmаstуx': 'uromastyx', 'аеgурtiа': 'aegyptia', 'cаlаmus': 'calamus',
}


def clean(text):
    text = strip_arabic(text)
    for bad, good in OCR_FIXES.items():
        if bad in text:
            text = text.replace(bad, good)
    # сатр ичидаги ортиқча бўшлиқларни йиғиштириш
    lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in text.split('\n')]
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    text = re.sub(r' +([,.;:!?»])', r'\1', text)  # тиниш белгиси олдидаги бўшлиқ
    return text


def parse_fn_defs(lines):
    """Сатрлардан footnote таърифларини йиғиш. Бир сатрда бир неча таъриф
    бўлиши мумкин: '[3] Жума... [4] Исро...'"""
    fd = {}
    for ln in lines:
        if not ln.lstrip().startswith('['):
            continue
        for m in re.finditer(r'\[(\d+)\]\s*([^\[]*)', ln):
            txt = strip_arabic(m.group(2)).strip()
            if txt:
                fd[int(m.group(1))] = txt
    return fd


def make_fn_inliner(fdict):
    def repl(m):
        n = int(m.group(1))
        if n in fdict:
            t = fdict[n].strip().rstrip(' .')
            return ' (' + t + ')'
        return m.group(0)
    return repl


# матн ичида келадиган footnote таърифлари (масалан "...сўзи.[7] Нисо сураси,
# 101-оят.") — оят/сура/ҳадис ҳаволаси шаклидаги таърифларни ажратиб олиб,
# ҳаволаларни (...) шаклига киритамиз.
_INLINE_DEF = re.compile(
    r'\s*\[(\d+)\]\s+([^\[\]]*?(?:сураси|сўзи|оят|оятлар|ҳадис|ҳадисга|қаранг)[^\[\]]*?\.)')


def inline_footnotes(text, fdict):
    local = dict(fdict)

    def collect(m):
        local[int(m.group(1))] = m.group(2).strip()
        return ''
    text = _INLINE_DEF.sub(collect, text)
    return re.sub(r'\[(\d+)\]', make_fn_inliner(local), text)


# ---------------------------------------------------------------------------
# 1) Файлни сатрларга ажратиш, ИЛОВАЛАР чегарасини топиш
# ---------------------------------------------------------------------------
with open(SRC, encoding='utf-8') as f:
    raw_lines = f.read().split('\n')

ilova_idx = None
for i, ln in enumerate(raw_lines):
    if ln.strip() == 'ILOVALAR':
        ilova_idx = i
        break

main_lines = raw_lines[:ilova_idx] if ilova_idx else raw_lines
ilova_lines = raw_lines[ilova_idx + 2:] if ilova_idx else []


# ---------------------------------------------------------------------------
# 2) ИЛОВАЛАР ни таҳлил қилиш: hadis_id -> матн
# ---------------------------------------------------------------------------
appendix_by_hadis = {}
appendix_leftover = []   # ҳадисга боғланмаган (масалан "N-боб...")

i = 0
N = len(ilova_lines)
while i < N:
    ln = ilova_lines[i].strip()
    # сарлавҳа: иккита DASH орасидаги матн
    if ln.endswith(':') and ('-ҳадис' in ln or '-боб' in ln):
        header = ln
        i += 1
        body = []
        while i < N:
            l2 = ilova_lines[i]
            if l2.strip() == DASH or l2.strip() == EQ:
                # кейинги сарлавҳа DASH...header...DASH кўринишида
                # текшириб кўрамиз: DASH дан кейин сарлавҳа борми
                j = i + 1
                if j < N and ilova_lines[j].strip().endswith(':') and \
                   ('-ҳадис' in ilova_lines[j] or '-боб' in ilova_lines[j]):
                    break
                # DASH ни ўтказиб юбориш
                i += 1
                continue
            if not is_arabic_line(l2):
                body.append(l2)
            i += 1
        text = clean('\n'.join(body))
        if '-ҳадис' in header:
            left = header.split('-ҳадис')[0]
            ids = [int(x) for x in re.findall(r'\d+', left)]
            for hid in ids:
                appendix_by_hadis.setdefault(hid, []).append(text)
        else:
            appendix_leftover.append((header, text))
    else:
        i += 1


# ---------------------------------------------------------------------------
# 3) Асосий таҳлил: китоб -> боб -> ҳадис
# ---------------------------------------------------------------------------
books = []
cur_book = None
cur_bob = None
cur_hadis = None
prev_bob_fn = {}   # олдинги бобнинг footnote'лари (олдинга ишора учун)

# дастлаб биринчи KITOB гача ҳамма нарсани (МУҚАДДИМА, МУНДАРИЖА) ташлаймиз
started = False


def finalize_hadis():
    global cur_hadis
    if cur_hadis is not None and cur_bob is not None:
        cur_bob['_hadis_raw'].append(cur_hadis)
    cur_hadis = None


def finalize_bob():
    """Бобни тугатиш: footnote'ларни йиғиш, муаллақот/изоҳ/ҳадисларни шакллантириш."""
    global cur_bob, prev_bob_fn
    if cur_bob is None:
        return
    finalize_hadis()

    # боб footnote'лари (pre_lines дан) + олдинги боб (олдинга ишора)
    fdict = parse_fn_defs(cur_bob['_pre'])
    resolve = {**prev_bob_fn, **fdict}

    # --- боб сарлавҳаси (рақам кейинроқ кетма-кет берилади) ---
    # Сарлавҳада footnote'нинг фақат қисқа ҳаволасини («Сура, оят») қолдирамиз,
    # узун таржимаси боб изоҳига кўчирилади.
    title_overflow = []

    def title_repl(m):
        n = int(m.group(1))
        if n in resolve:
            t = resolve[n].strip()
            cut = len(t)
            for sep in ('. ', ': ', ':«', ': «', '.«', ' – ', ' — '):
                i = t.find(sep)
                if i != -1:
                    cut = min(cut, i)
            short = t[:cut].rstrip(' .:')
            if len(t) > len(short) + 5:
                title_overflow.append(t)
            return ' (' + short + ')'
        return m.group(0)

    nomi_raw = cur_bob['_nomi_raw']
    title = re_bob_prefix.sub('', nomi_raw).strip()
    title = re.sub(r'[ \t]+', ' ', title)
    title = re.sub(r'\[(\d+)\]', title_repl, title).strip()
    cur_bob['_title'] = title

    # --- муаллақот / боб изоҳи (pre_lines, footnote-def ва арабча ташланади) ---
    content = [ln for ln in cur_bob['_pre']
               if ln.strip() and not re_fn_def.match(ln) and not is_arabic_line(ln)]
    mual, bizoh, in_izoh = [], [], False
    for ln in content:
        if not in_izoh and ln.lstrip().startswith('Изоҳ:'):
            in_izoh = True
            bizoh.append(re.sub(r'^\s*Изоҳ:\s*', '', ln))
            continue
        (bizoh if in_izoh else mual).append(ln)
    mual_t = inline_footnotes(clean('\n\n'.join(mual)), resolve) if mual else ''
    bizoh_t = inline_footnotes(clean('\n\n'.join(bizoh)), resolve) if bizoh else ''
    if mual_t:
        cur_bob['muallaqot'] = clean(mual_t)
    # сарлавҳадан кўчирилган узун оят таржималарини изоҳ бошига қўшамиз
    izoh_parts = title_overflow + ([bizoh_t] if bizoh_t else [])
    if izoh_parts:
        cur_bob['izoh'] = clean('\n\n'.join(izoh_parts))

    # --- ҳадислар ---
    hadises = []
    for hr in cur_bob['_hadis_raw']:
        h = build_hadis(hr, resolve)
        if h:
            hadises.append(h)
    # бир хил рақамли ҳадисларни («такрорий») битта ёзувга бирлаштириш
    merged, by_id = [], {}
    for h in hadises:
        if h['id'] in by_id:
            prev = by_id[h['id']]
            add = (h['rowi'] + ': ' if h.get('rowi') else '') + h['matn']
            prev['matn'] = (prev['matn'] + '\n\n' + add).strip()
            if h.get('izoh'):
                prev['izoh'] = ((prev.get('izoh', '') + '\n\n' + h['izoh']).strip())
        else:
            by_id[h['id']] = h
            merged.append(h)
    cur_bob['hadislar'] = merged

    # тозалаш
    for k in ('_pre', '_hadis_raw', '_nomi_raw'):
        cur_bob.pop(k, None)
    cur_book['boblar'].append(cur_bob)
    prev_bob_fn = fdict
    cur_bob = None


def build_hadis(hr, resolve):
    hid = hr['id']
    lines = [ln for ln in hr['lines'] if not is_arabic_line(ln)]
    # бўш сатрларни сақлаб, контент сатрларини ажратамиз
    content = [ln.strip() for ln in lines if ln.strip()]
    if not content:
        return None

    # ҳадис блоки ичидаги footnote таърифлари (боб ва олдинги боб устига)
    hadis_fn = parse_fn_defs(content)
    # footnote таъриф сатрлари матнга кирмаслиги керак
    content = [ln for ln in content if not re.match(r'^\[\d+\]\s', ln)]
    if not content:
        return None

    rowi = ''
    matn_lines, izoh_lines = [], []
    in_izoh = False

    # биринчи сатрдан ровийни ажратиш ("329, 330." ёки "1228 (такрорий)." бўлиши мумкин)
    first = content[0]
    m = re.match(r'^([\d,\s]+)(?:\s*\([^)]*\))?\.\s*(.*)$', first)
    start = 0
    if m:
        rest = m.group(2).strip()
        if '«' in rest:
            # тирноқ ичидаги матн шу сатрда: олдидагиси — ровий
            idx = rest.index('«')
            pre = rest[:idx].rstrip(' :')
            if pre:
                rowi = pre
            matn_lines.append(rest[idx:])
        elif rest.endswith(':'):
            # кириш жумласи (матн кейинги сатрларда)
            rowi = rest[:-1].strip()
        else:
            # тирноқсиз тўлиқ ривоят — бу матннинг ўзи
            matn_lines.append(rest)
        start = 1
    # қолган сатрлар
    for ln in content[start:]:
        if not in_izoh and ln.startswith('Изоҳ:'):
            in_izoh = True
            izoh_lines.append(re.sub(r'^Изоҳ:\s*', '', ln))
            continue
        if in_izoh:
            izoh_lines.append(ln)
            continue
        if ln == 'Иловага қаранг.':
            continue
        matn_lines.append(ln)

    fdict = {**resolve, **hadis_fn}
    matn = inline_footnotes(clean('\n\n'.join(matn_lines)), fdict)
    izoh = inline_footnotes(clean('\n\n'.join(izoh_lines)), fdict) if izoh_lines else ''
    rowi = inline_footnotes(rowi, fdict).strip()

    # ИЛОВАЛАР дан тегишли матнни izoh га қўшиш (блокдаги ҳамма рақам учун)
    extra_parts = []
    for n in hr.get('ids', [hid]):
        if n in appendix_by_hadis:
            extra_parts.extend(appendix_by_hadis[n])
    if extra_parts:
        extra = '\n\n'.join(extra_parts)
        izoh = (izoh + '\n\n' + extra).strip() if izoh else extra

    h = {'id': hid, 'matn': clean(matn)}
    if rowi:
        h['rowi'] = rowi
    if izoh:
        h['izoh'] = clean(izoh)
    return h


# асосий итерация
k = 0
M = len(main_lines)
skip_kirish = False
while k < M:
    ln = main_lines[k]
    s = ln.strip()

    mk = re_kitob.match(ln)
    if mk:
        finalize_bob()
        cur_book = {'id': int(mk.group(1)), 'nomi': kitob_name(mk.group(2)), 'boblar': []}
        books.append(cur_book)
        prev_bob_fn = {}
        started = True
        skip_kirish = False
        k += 1
        # кейинги "Arabcha:" сатрини ўтказиб юбориш
        continue

    if not started:
        k += 1
        continue

    mb = re_bob.match(ln)
    if mb:
        finalize_bob()
        skip_kirish = False
        cur_bob = {'id': int(mb.group(2)), '_nomi_raw': mb.group(3),
                   '_pre': [], '_hadis_raw': []}
        # кейинги арабча боб сатри ва DASH автоматик ташланади
        k += 1
        continue

    mh = re_hadis.match(ln)
    if mh:
        finalize_hadis()
        ids = [int(x) for x in re.findall(r'\d+', mh.group(1))]
        cur_hadis = {'id': ids[0], 'ids': ids, 'lines': []}
        k += 1
        continue

    # [Kirish] — китоб даражасидаги кириш, ташланади (боб бошлангунча)
    if s == '[Kirish]':
        skip_kirish = True
        k += 1
        continue

    # сепараторлар ва "Arabcha:" сатри
    if s == EQ or s == DASH or s.startswith('Arabcha:'):
        k += 1
        continue

    # контент сатрларини жорий контейнерга йиғиш
    if cur_hadis is not None:
        cur_hadis['lines'].append(ln)
    elif cur_bob is not None and not skip_kirish:
        cur_bob['_pre'].append(ln)
    # акс ҳолда (kirish ёки боб ташқариси) — ташлаб юборилади

    k += 1

finalize_bob()


# ---------------------------------------------------------------------------
# 4) Сақлаш + ҳисобот
# ---------------------------------------------------------------------------
# Китоб id'ларини кетма-кет 1..N қилиб бериш (манбада 86 икки марта рақамланган)
for idx, b in enumerate(books, 1):
    b['id'] = idx

# Боб id'ларини ҳар китоб ичида кетма-кет 1..N қилиб бериш
# (манбада "Такрорий" боблар бир хил рақамга эга)
for b in books:
    for pos, bo in enumerate(b['boblar'], 1):
        bo['id'] = pos
        t = bo.pop('_title', '')
        bo['nomi'] = f"{pos}-БОБ. {t}" if t else f"{pos}-БОБ"
    # калитлар тартиби: id, nomi, ... , hadislar
    for bo in b['boblar']:
        ordered = {'id': bo['id'], 'nomi': bo['nomi']}
        if 'muallaqot' in bo:
            ordered['muallaqot'] = bo['muallaqot']
        if 'izoh' in bo:
            ordered['izoh'] = bo['izoh']
        ordered['hadislar'] = bo['hadislar']
        bo.clear()
        bo.update(ordered)

# Якуний тозалаш: ҳал бўлмаган [N] footnote ҳаволаларини олиб ташлаш
# (таърифи доирада топилмаган — масалан сарлавҳа ёки китоб номидаги) ва
# қолган қўш бўшлиқларни йиғиштириш.
def final_clean(s):
    s = re.sub(r'\s*\[\d+\]', '', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    s = re.sub(r' +([,.;:!?»])', r'\1', s)
    return s.strip()


for b in books:
    b['nomi'] = final_clean(b['nomi'])
    for bo in b['boblar']:
        bo['nomi'] = final_clean(bo['nomi'])
        for f in ('muallaqot', 'izoh'):
            if f in bo:
                bo[f] = final_clean(bo[f])
        for h in bo['hadislar']:
            h['matn'] = final_clean(h['matn'])
            for f in ('rowi', 'izoh'):
                if f in h:
                    h[f] = final_clean(h[f])

nb = len(books)
nbob = sum(len(b['boblar']) for b in books)
nh = sum(len(bo['hadislar']) for b in books for bo in b['boblar'])
matched_app = sum(1 for b in books for bo in b['boblar'] for h in bo['hadislar']
                  if 'izoh' in h)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(books, f, ensure_ascii=False, separators=(',', ':'))

print(f'Китоблар: {nb}')
print(f'Боблар:   {nbob}')
print(f'Ҳадислар: {nh}')
print(f'ИЛОВА (ҳадисга боғланган уникал): {len(appendix_by_hadis)}')
print(f'ИЛОВА боғланмаган (боб ва ҳ.к.): {len(appendix_leftover)}')
for hdr, _ in appendix_leftover:
    print('   leftover:', hdr)
