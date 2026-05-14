"""Build new data.json from all .docx files using parse_docx."""
import json, os, re
from parse_docx import parse_docx

# Mapping: canonical_book_id -> .docx file name(s) (list for merge cases)
MAPPING = {
    1: ['Ваҳийнинг бошланиши китоби.docx'],
    2: ['Иймон китоби.docx'],
    3: ['Илм китоби.docx'],
    4: ['Таҳорат китоби.docx'],
    5: ['Ғусл китоби.docx'],
    6: ['Ҳайз китоби.docx'],
    7: ['Таяммум китоби.docx'],
    8: ['Намоз китоби.docx'],
    9: ['Намоз вақтлари китоби.docx'],
    10: ['Азон китоби.docx'],
    11: [],  # Жума - missing
    12: ['Хавф намози китоби.docx'],
    13: ['Икки ҳайит китоби.docx'],
    14: ['Витр китоби.docx'],
    15: ['Истисқо китоби.docx'],
    16: ['Кусуф китоби.docx'],
    17: ['Қуръон саждалари китоби.docx'],
    18: ['Намозни қаср қилиш китоби.docx'],
    19: ['Таҳажжуд китоби.docx'],
    20: ['Макка ва Мадина масжидидаги намознинг фазилати китоби.docx'],
    21: ['Намоздаги ҳаракъат китоби.docx'],
    22: ['Саҳв китоби.docx'],
    23: ['Жанозалар Китоби.docx'],
    24: ['Закот китоби.docx'],
    25: ['Ҳаж китоби.docx'],
    26: ['Умра китоби.docx'],
    27: ['Муҳсар китоби.docx'],
    28: ['Ов жазоси китоби.docx'],
    29: ['Мадинанинг фазилатлари.docx'],
    30: ['Рўза.docx', 'Руза китоби.docx'],
    31: ['Таровеҳ намози.docx'],
    32: ['Қадр кечасининг фазли.docx'],
    33: ['Эътикоф.docx'],
    34: ['Савдо китоби.docx'],
    35: ['Салам_ китоби ҳақида.docx'],
    36: ['Шуфъа_.docx'],
    37: ['Ижара_ ҳақида.docx'],
    38: ['Ҳаволалар_ ҳақида.docx'],
    39: ['Кафола_.docx'],
    40: ['Ваколат_ ҳақида.docx'],
    41: ['Музораъа_.docx'],
    42: ['Мусоқот_.docx'],
    43: ['Қарзларни талаб қилиш, қарзларни адо қилиш, музлатиш ва муфлисни (банкротни) эълон қилиш китоби.docx'],
    44: ['Хусуматлар китоби.docx'],
    45: ['Топиб олинган нарса китоби.docx'],
    46: ['Ноҳақ олинган моллар китоби.docx'],
    47: ['Шерикчилик китоби.docx'],
    48: ['Гаров китоби.docx'],
    49: ['Қул озод қилиш китоби.docx'],
    50: ['Мукотаб_ ҳақида.docx'],
    51: ['Ҳиба ва унинг фазли китоби.docx'],
    52: ['Гувоҳликлар.docx'],
    53: ['Сулҳ.docx'],
    54: ['Шартлар.docx'],
    55: ['Васиятлар.docx'],
    56: ['Жиҳод ва юришларнинг фазли ҳақида.docx'],
    57: ['Хумуснинг фарзлиги китоби.docx'],
    58: ['Жизя ва битим (сулҳ) китоби.docx'],
    59: ['Яратишнинг (яралишнинг) бошланиши китоби.docx'],
    60: ['Анбиёлар ҳадислари китоби.docx'],
    61: ['Китоб Маноқиб (мақтовга сазовор хислатлар) хусусида.docx'],
    62: ['Китоб саҳобаларнинг фазилати.docx'],
    63: ['Китоб ансорларнинг маноқиблари ҳақида.docx'],
    64: ['Китоб ул-мағозий.docx'],
    65: ['Тафсир китоби.docx'],
    66: ['Қуръон Фазийлатлари.docx'],
    67: ['Никоҳ.docx'],
    68: ['Талоқ китоби.docx'],
    69: ['Нафақалар.docx'],
    70: ['Таомлар.docx'],
    71: ['Ақийқа.docx'],
    72: ['Сўйишлар.docx'],
    73: ['Қурбонликлар китоби.docx'],
    74: ['Ичимликлар китоби.docx'],
    75: ['Беморлар китоби.docx'],
    76: ['Тиб китоби.docx'],
    77: ['Либос китоби.docx'],
    78: ['Адаб (китоби).docx'],
    79: ['Изн сўраш китоби.docx'],
    80: ['Дуолар китоби.docx'],
    81: ['Латоиф китоби.docx'],
    82: ['Қадар китоби.docx'],
    83: ['Қасамлар ва назрлар китоби.docx'],
    84: ['Қасамлар Каффоратлари Боби.docx'],
    85: ['Фароиз китоби.docx'],
    86: ['Ҳаддлар китоби.docx'],
    87: ['Товонлар китоби.docx'],
    88: ['Муртад ва ҳаққа қарши чиқувчиларни тавба қилдириш ҳамда уларга қарши уриш қилиш китоби.docx'],
    89: ['Мажбур қилиш китоби.docx'],
    90: ['Ҳийлалар китоби.docx', 'Ҳийлалар китоби (1).docx'],
    91: ['(Тушларни) таъбир қилиш китоби.docx'],
    92: ['Фитналар китоби.docx'],
    93: ['Ҳукмлар китоби.docx'],
    94: ['Орзу истаклар китоби.docx'],
    95: ['Ёлғиз шахслар томонидан берилган ҳабарлар китоби.docx'],
    96: [],  # Эътисом - missing
    97: ['Тавҳид китоби.docx'],
}

def merge_parsed(parsed_list):
    """Merge chapters from multiple parsed docx outputs.

    If hadis IDs overlap, dedupe by ID (later one wins for now).
    If chapters don't overlap (different hadith ranges), simply append.
    """
    if not parsed_list: return []
    if len(parsed_list) == 1: return parsed_list[0]
    merged = list(parsed_list[0])
    seen_h = {h['id'] for c in merged for h in c['hadislar']}
    last_chap_id = merged[-1]['id'] if merged else 0
    for parsed in parsed_list[1:]:
        for c in parsed:
            last_chap_id += 1
            new_c = dict(c)
            new_c['id'] = last_chap_id
            new_c['hadislar'] = [h for h in c['hadislar'] if h['id'] not in seen_h]
            for h in new_c['hadislar']:
                seen_h.add(h['id'])
            if new_c['hadislar'] or new_c.get('muallaqot') or new_c.get('nomi'):
                merged.append(new_c)
    return merged

def main():
    # Load existing data.json to keep book names (nomi). Fall back to backup if needed.
    src = 'data.json.bak' if os.path.exists('data.json.bak') else 'data.json'
    with open(src) as f:
        existing = json.load(f)
    existing_names = {k['id']: k['nomi'] for k in existing}
    # Fix placeholder name for book 63
    if existing_names.get(63) == '63-китоб':
        existing_names[63] = 'Ансорларнинг маноқиблари китоби'

    out = []
    for kid in range(1, 98):
        files = MAPPING.get(kid, [])
        nomi = existing_names.get(kid, f'{kid}-китоб')
        if not files:
            # Empty book
            out.append({'id': kid, 'nomi': nomi, 'boblar': []})
            continue
        parsed_list = []
        for fn in files:
            path = f'buxoriy kitoblari/{fn}'
            if not os.path.exists(path):
                print(f'WARNING: missing file {fn}')
                continue
            parsed_list.append(parse_docx(path))
        merged = merge_parsed(parsed_list)
        out.append({'id': kid, 'nomi': nomi, 'boblar': merged})

    # Save
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    # Print summary
    print(f'Жами китоблар: {len(out)}')
    total_boblar = 0
    total_hadis = 0
    for k in out:
        nb = len(k['boblar'])
        nh = sum(len(c['hadislar']) for c in k['boblar'])
        first_h = k['boblar'][0]['hadislar'][0]['id'] if (nb and k['boblar'][0]['hadislar']) else '—'
        last_h = '—'
        for c in reversed(k['boblar']):
            if c['hadislar']:
                last_h = c['hadislar'][-1]['id']
                break
        total_boblar += nb
        total_hadis += nh
        marker = '✓' if nb > 0 else '✗'
        print(f'  {marker} {k["id"]:>3}: {k["nomi"][:35]:35} — {nb:>3} боб, {nh:>4} ҳадис ({first_h}–{last_h})')
    print(f'Жами: {total_boblar} боб, {total_hadis} ҳадис')

if __name__ == '__main__':
    main()
