#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pdf.py — data.json дан чиройли терилган PDF китоб(лар) генерация қилади.

Натижа:
  pdf/buxoriy-sahih-toliq.pdf        — барча 98 китоб битта файлда
  pdf/kitoblar/NN-<номи>.pdf         — ҳар китоб алоҳида

Фойдаланиш:
  python3 build_pdf.py            # ҳаммаси (тўлиқ + китобма-китоб)
  python3 build_pdf.py --full     # фақат тўлиқ файл
  python3 build_pdf.py --books    # фақат китобма-китоб

Эслатма: фақат ўзбекча матн киритилади (арабча йўқ).
Боб номи index.html даги bobNomi() / fmtBobTitle() мантиғи билан бир хил форматланади.
"""
import json
import os
import re
import sys

from fpdf import FPDF

FONT_DIR = '/usr/share/fonts/truetype/freefont'
OUT_DIR = 'pdf'
SITE_URL = 'https://abuyahyo.github.io/buxoriy/'

# ── Боб номини форматлаш (index.html bobNomi/fmtBobTitle билан мос) ──────────

def fmt_bob_title(rest):
    rest = rest.lower()
    rest = re.sub(r'(^|[.?!»«(]\s*)([а-яёҳқғўa-z])',
                  lambda m: m.group(1) + m.group(2).upper(), rest)
    rest = re.sub(r'(\s)Деган(\s)', r'\1деган\2', rest)
    rest = rest.replace('набий', 'Набий')
    rest = re.sub(r'(?<!солла)аллоҳ(?!\s*у\s*алайҳи)', 'Аллоҳ', rest)
    rest = rest.replace('муҳаммад', 'Муҳаммад')
    return rest


def bob_nomi(nomi):
    if ' // ' in nomi:
        nums, titles = [], []
        for p in nomi.split(' // '):
            mm = re.match(r'^\s*(\d+)\s*-\s*[Бб][Оо][Бб]\.?\s*([\s\S]*)$', p)
            if mm:
                nums.append(int(mm.group(1)))
                t = re.sub(r'^\(такрорий\)\.?\s*', '', mm.group(2).strip(), flags=re.I).strip()
                if t:
                    titles.append(t)
        if nums:
            if len(nums) == 2 and nums[1] == nums[0] + 1:
                nl = f'{nums[0]}–{nums[1]}'
            else:
                nl = ', '.join(map(str, nums))
            r = nl + '-БОБ'
            if titles:
                ft = fmt_bob_title('. '.join(titles))
                if not re.search(r'[.?!…»]$', ft):
                    ft += '.'
                r += '. ' + ft
            return r
    m = re.match(r'^(\d+-[Бб][Оо][Бб]\.?\s*)([\s\S]*)', nomi)
    if not m:
        return nomi
    prefix = m.group(1).upper()
    rest = fmt_bob_title(m.group(2))
    if not re.search(r'[.?!…»]$', rest):
        return prefix + rest + '.'
    return prefix + rest


# ── PDF ──────────────────────────────────────────────────────────────────────

class Book(FPDF):
    def __init__(self):
        super().__init__(format='A4')
        self.set_margins(20, 18, 20)
        self.set_auto_page_break(True, margin=18)
        self.add_font('serif', '', f'{FONT_DIR}/FreeSerif.ttf')
        self.add_font('serif', 'B', f'{FONT_DIR}/FreeSerifBold.ttf')
        self.add_font('serif', 'I', f'{FONT_DIR}/FreeSerifItalic.ttf')
        self.add_font('serif', 'BI', f'{FONT_DIR}/FreeSerifBoldItalic.ttf')
        self.running_title = ''

    def footer(self):
        self.set_y(-13)
        self.set_font('serif', 'I', 9)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, str(self.page_no()), align='C')

    def header(self):
        if self.page_no() == 1 or not self.running_title:
            return
        self.set_font('serif', 'I', 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 6, self.running_title, align='C')
        self.ln(3)
        self.set_draw_color(220, 220, 220)
        self.line(self.l_margin + 30, self.get_y(), self.w - self.r_margin - 30, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)


SAGE = (74, 103, 65)
DIM = (90, 90, 90)
MUTED = (130, 130, 130)


def write_para(pdf, text, size, style='', color=(0, 0, 0), align='J',
               lh=1.55, space_after=2.0):
    """\\n\\n параграфларни ва \\n сатр кўчишларни ҳисобга олиб ёзади."""
    pdf.set_font('serif', style, size)
    pdf.set_text_color(*color)
    line_h = size * lh * 0.3528  # pt → mm коэффициент
    paras = text.split('\n\n')
    for i, para in enumerate(paras):
        para = para.strip('\n')
        if not para:
            continue
        pdf.multi_cell(0, line_h, para, align=align)
        if i < len(paras) - 1:
            pdf.ln(line_h * 0.45)
    pdf.ln(space_after)


def render_book(pdf, k):
    pdf.add_page()
    # Китоб сарлавҳаси
    pdf.ln(6)
    pdf.set_font('serif', 'B', 11)
    pdf.set_text_color(*SAGE)
    pdf.cell(0, 7, f"{k['id']}-КИТОБ", align='C')
    pdf.ln(9)
    pdf.set_font('serif', 'B', 19)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 9, k['nomi'].replace('*', ''), align='C')
    pdf.ln(6)
    pdf.set_draw_color(*SAGE)
    cx = pdf.w / 2
    pdf.line(cx - 25, pdf.get_y(), cx + 25, pdf.get_y())
    pdf.ln(8)

    for b in k.get('boblar', []):
        # Боб сарлавҳаси
        if pdf.get_y() > pdf.h - 60:
            pdf.add_page()
        pdf.ln(3)
        pdf.set_font('serif', 'B', 13)
        pdf.set_text_color(*SAGE)
        pdf.multi_cell(0, 6.5, bob_nomi(b['nomi']), align='L')
        pdf.ln(1.5)

        if b.get('muallaqot'):
            write_para(pdf, b['muallaqot'], 10.5, 'I', DIM, align='L', space_after=1.5)
        if b.get('izoh'):
            write_para(pdf, b['izoh'], 10, '', DIM, align='L', space_after=1.5)

        for h in b.get('hadislar', []):
            if pdf.get_y() > pdf.h - 45:
                pdf.add_page()
            pdf.ln(3)
            # Ҳадис рақами
            pdf.set_font('serif', 'B', 10)
            pdf.set_text_color(*MUTED)
            num = f"{h['id']}-ҲАДИС"
            pdf.cell(0, 6, '· ' + num + ' ·', align='C')
            pdf.ln(8)
            # Ровий
            if h.get('rowi'):
                write_para(pdf, h['rowi'], 11, 'I', DIM, align='L',
                           lh=1.4, space_after=1.2)
            # Матн
            if h.get('matn'):
                write_para(pdf, h['matn'], 12, '', (15, 15, 15),
                           align='J', lh=1.6, space_after=1.5)
            # Изоҳ
            if h.get('izoh'):
                write_para(pdf, h['izoh'], 10, '', DIM, align='L',
                           lh=1.5, space_after=1.0)
            # Манба
            if h.get('manba'):
                write_para(pdf, h['manba'], 9.5, 'I', MUTED, align='L',
                           lh=1.4, space_after=1.0)


def title_page(pdf, subtitle):
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font('serif', 'B', 30)
    pdf.set_text_color(*SAGE)
    pdf.multi_cell(0, 14, 'Ал-Жомиъ ас-Саҳиҳ', align='C')
    pdf.ln(4)
    pdf.set_font('serif', 'I', 15)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 9, 'Имом Бухорий', align='C')
    pdf.ln(10)
    pdf.set_draw_color(*SAGE)
    cx = pdf.w / 2
    pdf.line(cx - 30, pdf.get_y(), cx + 30, pdf.get_y())
    pdf.ln(12)
    pdf.set_font('serif', '', 13)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 8, subtitle, align='C')
    pdf.ln(40)
    pdf.set_font('serif', 'I', 10)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 6, SITE_URL, align='C')


def build_full(db):
    pdf = Book()
    pdf.set_title('Саҳиҳул Бухорий — тўлиқ')
    pdf.set_author('Имом Бухорий')
    title_page(pdf, f'Ўзбекча таржима\n\nТўлиқ тўплам — {len(db)} китоб')
    for k in db:
        pdf.running_title = k['nomi'].replace('*', '')
        render_book(pdf, k)
    path = os.path.join(OUT_DIR, 'buxoriy-sahih-toliq.pdf')
    pdf.output(path)
    return path


def build_books(db):
    bdir = os.path.join(OUT_DIR, 'kitoblar')
    os.makedirs(bdir, exist_ok=True)
    paths = []
    for k in db:
        pdf = Book()
        pdf.set_title(f"{k['id']}-китоб — {k['nomi']}")
        pdf.set_author('Имом Бухорий')
        pdf.running_title = k['nomi'].replace('*', '')
        render_book(pdf, k)
        fn = f"kitob-{k['id']:02d}.pdf"
        path = os.path.join(bdir, fn)
        pdf.output(path)
        paths.append(path)
    return paths


def main():
    args = set(sys.argv[1:])
    do_full = '--full' in args or not (args & {'--full', '--books'})
    do_books = '--books' in args or not (args & {'--full', '--books'})

    with open('data.json', encoding='utf-8') as f:
        db = json.load(f)

    os.makedirs(OUT_DIR, exist_ok=True)

    if do_full:
        p = build_full(db)
        sz = os.path.getsize(p)
        print(f'✓ {p}  ({sz/1024/1024:.1f} МБ)')
    if do_books:
        paths = build_books(db)
        total = sum(os.path.getsize(p) for p in paths)
        print(f'✓ {len(paths)} та китоб → {OUT_DIR}/kitoblar/  (жами {total/1024/1024:.1f} МБ)')


if __name__ == '__main__':
    main()
