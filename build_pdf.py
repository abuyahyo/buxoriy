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

_BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(_BASE, 'fonts', 'Inter')
AR_FONT_DIR = os.path.join(_BASE, 'fonts', 'Amiri')
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
        self.add_font('ui', '', f'{FONT_DIR}/Inter-Regular.ttf')
        self.add_font('ui', 'B', f'{FONT_DIR}/Inter-Bold.ttf')
        self.add_font('ui', 'I', f'{FONT_DIR}/Inter-Italic.ttf')
        self.add_font('ui', 'BI', f'{FONT_DIR}/Inter-BoldItalic.ttf')
        # Арабча учун fallback (ўзбекча матн ичида учрайдиган арабча сўзлар).
        # Inter'да арабча глифлар йўқ — Amiri билан тўлдирамиз.
        self.add_font('amiri', '', f'{AR_FONT_DIR}/Amiri-Regular.ttf')
        self.set_fallback_fonts(['amiri'])
        # Эслатма: text shaping глобал ЁҚИЛМАЙДИ — у ҳар глифни алоҳида
        # позиция билан сақлаб, файлни жуда катта қилади. Фақат арабча
        # учрайдиган параграфларда write_para() ичида вақтинча ёқилади.
        self.running_title = ''

    def footer(self):
        self.set_y(-13)
        self.set_font('ui', 'I', 9)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, str(self.page_no()), align='C')

    def header(self):
        if self.page_no() == 1 or not self.running_title:
            return
        self.set_y(10)
        self.set_font('ui', 'I', 8.5)
        self.set_text_color(165, 165, 165)
        # Матн — катак y'ни кейинги сатрга суриб юборади (NEXT)
        self.cell(0, 5, self.running_title, align='C',
                  new_x="LMARGIN", new_y="NEXT")
        # Чизиқ — матн остида
        y = self.get_y() + 1.5
        self.set_draw_color(225, 225, 225)
        self.line(self.l_margin + 25, y, self.w - self.r_margin - 25, y)
        self.set_y(y + 5)
        self.set_text_color(0, 0, 0)


SAGE = (74, 103, 65)
DIM = (90, 90, 90)
MUTED = (130, 130, 130)

AR_RE = re.compile(r'[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]')


def write_para(pdf, text, size, style='', color=(0, 0, 0), align='J',
               lh=1.55, space_after=2.0):
    """\\n\\n параграфларни ва \\n сатр кўчишларни ҳисобга олиб ёзади.
    Арабча учраса — шу параграф учун text shaping вақтинча ёқилади
    (RTL/уланиш учун), бошқа ҳолда оддий (файл кичик қолади)."""
    pdf.set_font('ui', style, size)
    pdf.set_text_color(*color)
    line_h = size * lh * 0.3528  # pt → mm коэффициент
    paras = text.split('\n\n')
    for i, para in enumerate(paras):
        para = para.strip('\n')
        if not para:
            continue
        shaped = bool(AR_RE.search(para))
        if shaped:
            pdf.set_text_shaping(True)
        pdf.multi_cell(0, line_h, para, align=align)
        if shaped:
            pdf.set_text_shaping(False)
        if i < len(paras) - 1:
            pdf.ln(line_h * 0.45)
    pdf.ln(space_after)


def render_book(pdf, k):
    pdf.add_page()
    # Китоб сарлавҳаси
    pdf.ln(6)
    pdf.set_font('ui', 'B', 11)
    pdf.set_text_color(*SAGE)
    pdf.cell(0, 7, f"{k['id']}-КИТОБ", align='C')
    pdf.ln(9)
    pdf.set_font('ui', 'B', 19)
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
        pdf.set_font('ui', 'B', 14)
        pdf.set_text_color(*SAGE)
        pdf.multi_cell(0, 7, bob_nomi(b['nomi']), align='L')
        pdf.ln(1.5)

        if b.get('muallaqot'):
            write_para(pdf, b['muallaqot'], 11.5, 'I', DIM, align='L', space_after=1.5)
        if b.get('izoh'):
            write_para(pdf, b['izoh'], 11, '', DIM, align='L', space_after=1.5)

        for h in b.get('hadislar', []):
            if pdf.get_y() > pdf.h - 45:
                pdf.add_page()
            pdf.ln(3)
            # Ҳадис рақами
            pdf.set_font('ui', 'B', 10.5)
            pdf.set_text_color(*MUTED)
            num = f"{h['id']}-ҲАДИС"
            pdf.cell(0, 6, '· ' + num + ' ·', align='C')
            pdf.ln(8)
            # Ровий
            if h.get('rowi'):
                write_para(pdf, h['rowi'], 12, 'I', DIM, align='L',
                           lh=1.4, space_after=1.2)
            # Матн
            if h.get('matn'):
                write_para(pdf, h['matn'], 13, '', (15, 15, 15),
                           align='J', lh=1.6, space_after=1.5)
            # Изоҳ
            if h.get('izoh'):
                write_para(pdf, h['izoh'], 11, '', DIM, align='L',
                           lh=1.5, space_after=1.0)
            # Манба
            if h.get('manba'):
                write_para(pdf, h['manba'], 10, 'I', MUTED, align='L',
                           lh=1.4, space_after=1.0)


def title_page(pdf, subtitle):
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font('ui', 'B', 30)
    pdf.set_text_color(*SAGE)
    pdf.multi_cell(0, 14, 'Ал-Жомиъ ас-Саҳиҳ', align='C')
    pdf.ln(4)
    pdf.set_font('ui', 'I', 15)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 9, 'Имом Бухорий', align='C')
    pdf.ln(10)
    pdf.set_draw_color(*SAGE)
    cx = pdf.w / 2
    pdf.line(cx - 30, pdf.get_y(), cx + 30, pdf.get_y())
    pdf.ln(12)
    pdf.set_font('ui', '', 13)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 8, subtitle, align='C')
    pdf.ln(40)
    pdf.set_font('ui', 'I', 10)
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


# ── Арабча (arabic.json) ──────────────────────────────────────────────────────

def write_ar(pdf, text, size=17, lh=1.85):
    """Арабча матн — Amiri, RTL, ўнгга текислаб, text shaping билан."""
    pdf.set_font('amiri', '', size)
    pdf.set_text_color(15, 15, 15)
    line_h = size * lh * 0.3528
    pdf.set_text_shaping(True)
    for para in text.split('\n\n'):
        para = para.strip('\n')
        if not para:
            continue
        pdf.multi_cell(0, line_h, para, align='R')
    pdf.set_text_shaping(False)
    pdf.ln(2.0)


def render_book_arabic(pdf, k, ardict):
    pdf.add_page()
    pdf.ln(6)
    pdf.set_font('ui', 'B', 11)
    pdf.set_text_color(*SAGE)
    pdf.cell(0, 7, f"{k['id']}-КИТОБ", align='C')
    pdf.ln(9)
    pdf.set_font('ui', 'B', 19)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 9, k['nomi'].replace('*', ''), align='C')
    pdf.ln(6)
    pdf.set_draw_color(*SAGE)
    cx = pdf.w / 2
    pdf.line(cx - 25, pdf.get_y(), cx + 25, pdf.get_y())
    pdf.ln(8)

    for b in k.get('boblar', []):
        if pdf.get_y() > pdf.h - 60:
            pdf.add_page()
        pdf.ln(3)
        pdf.set_font('ui', 'B', 14)
        pdf.set_text_color(*SAGE)
        pdf.multi_cell(0, 7, bob_nomi(b['nomi']), align='L')
        pdf.ln(1.5)

        for h in b.get('hadislar', []):
            ar = ardict.get(str(h['id']))
            if not ar:
                continue
            if pdf.get_y() > pdf.h - 45:
                pdf.add_page()
            pdf.ln(3)
            pdf.set_font('ui', 'B', 10.5)
            pdf.set_text_color(*MUTED)
            pdf.cell(0, 6, f"· {h['id']}-ҲАДИС ·", align='C')
            pdf.ln(8)
            write_ar(pdf, ar)


def build_full_arabic(db, ardict):
    pdf = Book()
    pdf.set_title('Саҳиҳул Бухорий — арабча')
    pdf.set_author('Имом Бухорий')
    title_page(pdf, 'Арабча матн (асл)\n\nТўлиқ тўплам — {} китоб'.format(len(db)))
    for k in db:
        pdf.running_title = k['nomi'].replace('*', '')
        render_book_arabic(pdf, k, ardict)
    path = os.path.join(OUT_DIR, 'buxoriy-arab-toliq.pdf')
    pdf.output(path)
    return path


def build_books_arabic(db, ardict):
    bdir = os.path.join(OUT_DIR, 'kitoblar')
    os.makedirs(bdir, exist_ok=True)
    paths = []
    for k in db:
        pdf = Book()
        pdf.set_title(f"{k['id']}-китоб (арабча) — {k['nomi']}")
        pdf.set_author('Имом Бухорий')
        pdf.running_title = k['nomi'].replace('*', '')
        render_book_arabic(pdf, k, ardict)
        fn = f"kitob-{k['id']:02d}-ar.pdf"
        path = os.path.join(bdir, fn)
        pdf.output(path)
        paths.append(path)
    return paths


def main():
    args = set(sys.argv[1:])
    modes = {'--full', '--books', '--ar', '--ar-books'}
    selected = args & modes
    # Ҳеч мод берилмаса — фақат ўзбекча (тўлиқ + китобма-китоб)
    do_full = '--full' in args or not selected
    do_books = '--books' in args or not selected
    do_ar = '--ar' in args
    do_ar_books = '--ar-books' in args

    with open('data.json', encoding='utf-8') as f:
        db = json.load(f)

    os.makedirs(OUT_DIR, exist_ok=True)

    if do_full:
        p = build_full(db)
        print(f'✓ {p}  ({os.path.getsize(p)/1024/1024:.1f} МБ)')
    if do_books:
        paths = build_books(db)
        total = sum(os.path.getsize(p) for p in paths)
        print(f'✓ {len(paths)} та китоб → {OUT_DIR}/kitoblar/  (жами {total/1024/1024:.1f} МБ)')
    if do_ar or do_ar_books:
        with open('arabic.json', encoding='utf-8') as f:
            ardict = json.load(f)
        if do_ar:
            p = build_full_arabic(db, ardict)
            print(f'✓ {p}  ({os.path.getsize(p)/1024/1024:.1f} МБ)')
        if do_ar_books:
            paths = build_books_arabic(db, ardict)
            total = sum(os.path.getsize(p) for p in paths)
            print(f'✓ {len(paths)} та арабча китоб → {OUT_DIR}/kitoblar/  (жами {total/1024/1024:.1f} МБ)')


if __name__ == '__main__':
    main()
