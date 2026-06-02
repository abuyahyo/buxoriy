# -*- coding: utf-8 -*-
"""arabic.json ни каноник манбадан (ar_source.json) генерация қилади.

Ҳар бир ўзбекча ҳадис `canon_no` (каноник Бухорий рақами) майдонига эга.
ar_source.json ҳам шу каноник рақам (hadithnumber) бўйича калитланган тўлиқ,
ҳаракатли арабча матнни сақлайди. Шунинг учун рақам бўйича тўғридан-тўғри
(ишончли) мослик: arabic.json[ўзбекча id] = каноник арабча матн.
"""
import json
import re

src = json.load(open('ar_source.json', encoding='utf-8'))['hadiths']
bytxt = {}
for h in src:
    t = (h.get('text') or '').strip()
    n = re.sub(r'\D', '', str(h.get('hadithnumber', '')))
    if t and n:
        bytxt.setdefault(int(n), t)

db = json.load(open('data.json', encoding='utf-8'))
arabic = {}
for b in db:
    for bo in b['boblar']:
        for h in bo['hadislar']:
            cn = re.sub(r'\D', '', str(h.get('canon_no', '')))
            if cn and int(cn) in bytxt:
                arabic.setdefault(str(h['id']), bytxt[int(cn)])

with open('arabic.json', 'w', encoding='utf-8') as f:
    json.dump(arabic, f, ensure_ascii=False, separators=(',', ':'))

import os
total = sum(len(bo['hadislar']) for b in db for bo in b['boblar'])
print('arabic.json:', len(arabic), '/', total,
      '(%.1f%%)' % (100*len(arabic)/total),
      '| %.2f MB' % (os.path.getsize('arabic.json')/1024/1024))
