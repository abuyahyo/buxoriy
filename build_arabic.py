# -*- coding: utf-8 -*-
"""arabic.json ни тоза арабча манбадан (sahih_bukhari_arabic.txt) генерация қилади.

Манбадаги (sahihul-buxoriy.txt) арабча «presentation forms» бузуқ кодлашда
бўлгани учун, бу скрипт:
  1. Бизнинг ҳар ҳадис учун бузуқ арабчани «скелет» (ундош) ҳолатига тиклайди.
  2. Тоза манба (sahih_bukhari_arabic.txt, кетма-кет рақамлаш) билан мазмун
     бўйича мослаштиради (sequence alignment) — чунки рақамлаш фарқ қилади.
  3. Бизнинг ҳадис id си → тоза арабча матн (arabic.json) ясайди.
Фақат ишончли (юқори LCP) мосликлар сақланади.
"""
import re
import json
import unicodedata
import difflib
import bisect

SRC = 'sahihul-buxoriy.txt'
CLEAN = 'sahih_bukhari_arabic.txt'
STD = 'sahih_bukhari_arabic_standard.txt'  # standart 1—7563 раqамлаш
OUT = 'arabic.json'

AR = re.compile(r'[؀-ۿﭐ-﷿ﹰ-﻿﴾﴿]')
re_kitob = re.compile(r'^(\d+)-KITOB:')
re_hadis = re.compile(r'^\[Hadis\s+([\d,\s]+?)(?:\s*\([^)]*\))?\.?\]\s*$')


def is_ar(s):
    s2 = s.replace(' ', '')
    return bool(s2) and len(AR.findall(s2)) / len(s2) > 0.4


def recon(t):
    """Бузуқ presentation-forms арабчани ундош скелетга тиклаш."""
    t = t.replace('ﴦﴥﴤ', 'لله')
    t = re.sub('ﵖ[ﭐ-﷿]?ﵐ', 'لا', t)
    t = ''.join(c for c in t if not (0xFB50 <= ord(c) <= 0xFDFF))
    return unicodedata.normalize('NFKC', t)


def skel(t):
    t = re.sub(r'[ًٌٍَُِّْـ]', '', t)
    for a, b in [('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ى', 'ي'),
                 ('ة', 'ه'), ('ؤ', 'و'), ('ئ', 'ي')]:
        t = t.replace(a, b)
    return re.sub(r'[^ا-ي]', '', t)


def lcp(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


# --- бизнинг ҳадислар (манба тартибида, арабча скелети билан) ---
our = []
started = cid = None
got = False
for ln in open(SRC, encoding='utf-8').read().split('\n'):
    if ln.strip() == 'ILOVALAR':
        break
    if re_kitob.match(ln):
        started = True
    if not started:
        continue
    mh = re_hadis.match(ln)
    if mh:
        cid = int(re.findall(r'\d+', mh.group(1))[0])
        got = False
        continue
    if cid and not got and is_ar(ln):
        body = re.sub(r'^\s*\d+\s*[ﻡم]?\s*-\s*', '', ln)
        our.append((cid, skel(recon(body))))
        got = True

# --- тоза манба (мҳashim6 — кетма-кет рақамлаш) ---
ftxt = open(CLEAN, encoding='utf-8').read()
fil = [(int(m.group(1)), m.group(2).strip(), skel(m.group(2)))
       for m in re.finditer(r'(?m)^(\d+)\.\s*(.+)$', ftxt)]
N = len(fil)

# --- стандарт манба (fawazahmed0 — 1—7563 халқаро рақамлаш) ---
# Бизнинг sahihul-buxoriy.txt ҳам шу рақамлашда (1—7563), шунинг учун
# раqам-бўйича тўғридан-тўғри мослик мумкин. Лекин ҳар бир мосликни
# исно скелет о'хшашлиги билан тасдиқлаймиз (хатоликнинг олдини олиш учун).
std_text = {}
std_skel = {}
for ln in open(STD, encoding='utf-8').read().split('\n'):
    m = re.match(r'^(\d+)\.\s*(.+)$', ln)
    if m:
        n = int(m.group(1))
        t = m.group(2).strip()
        if t and t != '[N/A]':
            std_text[n] = t
            std_skel[n] = skel(t)

# 0-босқич: РАҚАМ-БЎЙИЧА мослик (стандарт манбадан), исно-скелет тасдиғи билан
# Шарт: исно SequenceMatcher.ratio() ≥ 0.6 ВА LCP ≥ 15
# (мавжуд stage 1—4 фильтри 0.85/18 — кучлироқ; рақам ўзи асосий далил
# бўлгани учун бу ерда енгилроқ чегара ишлатилади, лекин тасдиқ сақланади.)
direct = {}      # oid -> арабча матн (стандарт манбадан)
direct_idx = set()  # our_index қийматлари (stage 1—4 учун)
for i, (oid, os) in enumerate(our):
    sk = std_skel.get(oid)
    if not sk or len(os) < 12 or len(sk) < 12:
        continue
    r = difflib.SequenceMatcher(None, os[:50], sk[:50]).ratio()
    l = lcp(os, sk)
    if r >= 0.6 and l >= 15:
        direct[oid] = std_text[oid]
        direct_idx.add(i)

# 1-босқич: глобал кетма-кетлик мослаштириш (иснод бошлари токен)
otok = [s[:30] for _, s in our]
ftok = [fs[:30] for _, _, fs in fil]
sm = difflib.SequenceMatcher(None, otok, ftok, autojunk=False)
omap = {}   # our_index -> fil_index
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        for k in range(i2 - i1):
            omap[i1 + k] = j1 + k


def expected(i, anchors):
    p = bisect.bisect_left(anchors, i)
    if p == 0:
        a = anchors[0]
        return omap[a] + (i - a)
    if p >= len(anchors):
        a = anchors[-1]
        return omap[a] + (i - a)
    a, b = anchors[p - 1], anchors[p]
    return round(omap[a] + (omap[b] - omap[a]) * (i - a) / (b - a))


# 2-босқич: интерполяция + ойнали LCP, бир неча марта (якорлар ўсади)
for win, thr in ((20, 24), (30, 22), (40, 20)):
    anchors = sorted(omap)
    if not anchors:
        break
    for i, (oid, os) in enumerate(our):
        if i in omap or len(os) < 12:
            continue
        exp = expected(i, anchors)
        best, bs = -1, 0
        for j in range(max(0, exp - win), min(N, exp + win + 1)):
            s = lcp(os, fil[j][2])
            if s > bs:
                bs, best = s, j
        if bs >= thr and best >= 0:
            omap[i] = best

# Тасдиқлаш: иснод (нарратор занжири) мослиги. Танчи (матн) тиклашда шовқин
# бўлгани учун тўлиқ матн эмас, балки иснод боши (~50 скелет белги) ишлатилади.
def isnad_ratio(i, fj):
    return difflib.SequenceMatcher(None, our[i][1][:50], fil[fj][2][:50]).ratio()


# our_index -> fil_index (фақат иснод>=0.85 ва LCP>=18 бўлганлар)
final = {}
seen_oid = set(direct)  # stage 0 топган oid'ларни такрор ишламаслик
for i, fj in omap.items():
    oid = our[i][0]
    if oid in seen_oid or lcp(our[i][1], fil[fj][2]) < 18:
        continue
    if isnad_ratio(i, fj) >= 0.85:
        final[i] = fj
        seen_oid.add(oid)

# 3-босқич: ТИКЛАШ — мос топилмаган ҳадислар учун манбадаги ишлатилмаган
# ҳадислардан, ишончли мослик якорлари асосида позицияни интерполяция қилиб,
# иснод>=0.88 шарти билан қидириш (бир неча марта — якорлар ўсади).
for _ in range(4):
    used = set(final.values())
    anchors = sorted(final)
    if not anchors:
        break
    added = 0
    for i, (oid, os) in enumerate(our):
        if i in final or oid in seen_oid or len(os) < 15:
            continue
        p = bisect.bisect_left(anchors, i)
        if p == 0:
            e = final[anchors[0]] + (i - anchors[0])
        elif p >= len(anchors):
            e = final[anchors[-1]] + (i - anchors[-1])
        else:
            a, b = anchors[p - 1], anchors[p]
            e = round(final[a] + (final[b] - final[a]) * (i - a) / (b - a))
        best, br = -1, 0.0
        for j in range(max(0, e - 45), min(N, e + 46)):
            if j in used:
                continue
            r = difflib.SequenceMatcher(None, os[:50], fil[j][2][:50]).ratio()
            if r > br:
                br, best = r, j
        if br >= 0.88 and best >= 0:
            final[i] = best
            used.add(best)
            seen_oid.add(oid)
            added += 1
    if not added:
        break

# 4-босқич: ГЛОБАЛ юқори-ишонч тиклаш — позицияга боғланмай, ишлатилмаган
# манба ҳадислари ичидан иснод>=0.92 ВА ягона (2-ўриндан >0.06 фарқли) бўлган
# мосликни қабул қилиш. Ягоналик шарти нотўғри (ўхшаш иснодли бошқа) мосликни
# четлайди.
used = set(final.values())
unused_idx = [j for j in range(N) if j not in used]
for i, (oid, os) in enumerate(our):
    if i in final or oid in seen_oid or len(os) < 15:
        continue
    scored = []
    for j in unused_idx:
        if j in used:
            continue
        r = difflib.SequenceMatcher(None, os[:50], fil[j][2][:50]).ratio()
        if r >= 0.85:
            scored.append((r, j))
    if not scored:
        continue
    scored.sort(reverse=True)
    best_r, best_j = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0
    if best_r >= 0.92 and (best_r - second) > 0.06:
        final[i] = best_j
        used.add(best_j)
        seen_oid.add(oid)

mapping = {}
# Stage 0 натижалари — биринчи навбатда
mapping.update(direct)
# Stage 1—4 натижалари — тўлдиргич
fallback_count = 0
for i, fj in final.items():
    oid = our[i][0]
    if oid not in mapping:
        mapping[oid] = fil[fj][1]
        fallback_count += 1

# Глобал такрорий рақамлар (бир id икки бобда, турли мазмун) — арабча рақам
# бўйича сақлангани учун бир нусхада нотўғри чиқар эди; уларни чиқариб ташлаймиз.
from collections import Counter
db = json.load(open('data.json', encoding='utf-8'))
idc = Counter(h['id'] for b in db for bo in b['boblar'] for h in bo['hadislar'])
dups = [i for i, c in idc.items() if c > 1]
for d in dups:
    mapping.pop(d, None)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False, separators=(',', ':'))

import os
db = json.load(open('data.json', encoding='utf-8'))
uniq = set(h['id'] for b in db for bo in b['boblar'] for h in bo['hadislar'])
cov = len(set(mapping) & uniq)
print('бизнинг ҳадис (арабчали):', len(our),
      '| мҳashim6:', N, '| стандарт:', len(std_text))
print('  Stage 0 (рақам+тасдиқ):', len(direct))
print('  Stage 1—4 (иснод-скелет):', fallback_count)
print('mapping:', len(mapping), '| қамров:', cov, '/', len(uniq),
      '(%.1f%%)' % (100 * cov / len(uniq)))
print('arabic.json: %.2f MB' % (os.path.getsize(OUT) / 1024 / 1024))
