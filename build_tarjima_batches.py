"""Таржимаси йўқ (tarjima_status='missing') ҳадисларни арабча матни билан
10 тадан батчларга бўлади (Gemini таржимаси учун). Чиқиш: tarjima/batch_NN.json.

  python3 build_tarjima_batches.py
"""
import json, os

db = json.load(open('data.json', encoding='utf-8'))
out = []
for k in db:
    for b in k['boblar']:
        for h in b['hadislar']:
            if h.get('tarjima_status') == 'missing':
                out.append({'id': h['id'], 'kitob': k['nomi'], 'bob': b['nomi'],
                            'canon_no': h.get('canon_no', ''),
                            'arabcha': (h.get('matn_ar') or '').strip()})

N = 10
os.makedirs('tarjima', exist_ok=True)
nb = (len(out) + N - 1) // N
for i in range(nb):
    fn = f'tarjima/batch_{i+1:02d}.json'
    json.dump(out[i*N:(i+1)*N], open(fn, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
print(f'{len(out)} ҳадис → {nb} батч ({N} тадан) → tarjima/')
