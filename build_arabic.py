# -*- coding: utf-8 -*-
"""sahihul-buxoriy.txt -> arabic.json

Ҳар бир ҳадиснинг арабча иснод+матнини ажратиб, алоҳида файлга сақлайди.
Илова бу файлни фақат фойдаланувчи «Арабча» тугмасини босганда юклайди.
Охиридаги ﺃﻃﺮﺍﻓﻪ (атраф) / ﺗﺤﻔﺔ (туҳфа) ҳавола рақамлари кесилади.
"""
import json
import re

SRC = 'sahihul-buxoriy.txt'
OUT = 'arabic.json'

AR = re.compile(r'[؀-ۿﭐ-﷿ﹰ-﻿﴾﴿]')
re_kitob = re.compile(r'^(\d+)-KITOB:')
re_hadis = re.compile(r'^\[Hadis\s+([\d,\s]+?)(?:\s*\([^)]*\))?\.?\]\s*$')

# атраф/туҳфа ва бошқа ҳавола маркерлари (presentation forms)
REF_MARKERS = ['ﺃﻃﺮﺍﻓﻪ', 'ﻃﺮﻓﺎﻩ', 'ﻃﺮﻓﻪ', 'ﺗﺤﻔﺔ', 'أطرافه', 'طرفاه', 'طرفه', 'تحفة']


def is_arabic_line(s):
    s2 = s.replace(' ', '')
    if not s2:
        return False
    return len(AR.findall(s2)) / len(s2) > 0.4


def trim_refs(s):
    cut = len(s)
    for mk in REF_MARKERS:
        i = s.find(mk)
        if i != -1:
            cut = min(cut, i)
    return s[:cut].strip().rstrip('-').strip()


with open(SRC, encoding='utf-8') as f:
    lines = f.read().split('\n')

# ILOVALAR гача
end = len(lines)
for i, ln in enumerate(lines):
    if ln.strip() == 'ILOVALAR':
        end = i
        break

arabic = {}
started = False
cur_id = None
cur_arab = None   # шу ҳадиснинг биринчи арабча сатри

for ln in lines[:end]:
    if re_kitob.match(ln):
        started = True
    if not started:
        continue
    mh = re_hadis.match(ln)
    if mh:
        cur_id = int(re.findall(r'\d+', mh.group(1))[0])
        cur_arab = None
        continue
    if cur_id is None:
        continue
    # ҳадис блокидаги биринчи арабча сатр — иснод+матн
    if cur_arab is None and is_arabic_line(ln):
        # бошидаги "N - " ёки "N ﻡ - " рақам-тире олиб ташланади
        body = re.sub(r'^\s*\d+\s*[ﻡم]?\s*-\s*', '', ln)
        body = trim_refs(body)
        if body:
            arabic[cur_id] = body
        cur_arab = ln

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(arabic, f, ensure_ascii=False, separators=(',', ':'))

import os
print('ҳадислар (арабча):', len(arabic))
print('arabic.json:', f'{os.path.getsize(OUT):,} bytes ({os.path.getsize(OUT)/1024/1024:.2f} MB)')
