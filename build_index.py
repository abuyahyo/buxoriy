"""Build lightweight index.json from data.json.

index.json contains book + chapter metadata (no hadith content) so the home
and book pages can render quickly before the full 7.6 MB data.json arrives.

Per-chapter:
- id, nomi, hC (hadis count), and optional izoh/muallaqot are kept.
- hadislar array is omitted.
"""
import json

with open('data.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

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

import os
data_size = os.path.getsize('data.json')
idx_size = os.path.getsize('index.json')
print(f'data.json:  {data_size:>10,} bytes ({data_size/1024/1024:.2f} MB)')
print(f'index.json: {idx_size:>10,} bytes ({idx_size/1024:.1f} KB)')
print(f'ratio: {idx_size/data_size*100:.1f}%')
