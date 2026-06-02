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

# --- тоза манба ---
ftxt = open(CLEAN, encoding='utf-8').read()
fil = [(int(m.group(1)), m.group(2).strip(), skel(m.group(2)))
       for m in re.finditer(r'(?m)^(\d+)\.\s*(.+)$', ftxt)]
N = len(fil)

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

# our_id -> тоза арабча. Тасдиқлаш: иснод (нарратор занжири) мослиги.
# Танчи (матн) тиклашда шовқин бўлгани учун тўлиқ матн эмас, балки иснод боши
# (биринчи ~50 скелет белги) ўхшашлиги ишлатилади: >=0.85 бўлса — ўша ҳадис.
# Бу иснод занжири фарқли (нотўғри) мосликларни четлайди.
mapping = {}
for i, fj in omap.items():
    oid, os = our[i]
    if oid in mapping or lcp(os, fil[fj][2]) < 18:
        continue
    fs = fil[fj][2]
    isnad = difflib.SequenceMatcher(None, os[:50], fs[:50]).ratio()
    if isnad >= 0.85:
        mapping[oid] = fil[fj][1]

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False, separators=(',', ':'))

import os
db = json.load(open('data.json'))
uniq = set(h['id'] for b in db for bo in b['boblar'] for h in bo['hadislar'])
cov = len(set(mapping) & uniq)
print('бизнинг ҳадис (арабчали):', len(our), '| тоза манба:', N)
print('mapping:', len(mapping), '| қамров:', cov, '/', len(uniq),
      '(%.1f%%)' % (100 * cov / len(uniq)))
print('arabic.json: %.2f MB' % (os.path.getsize(OUT) / 1024 / 1024))
