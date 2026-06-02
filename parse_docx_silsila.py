"""Олтин Силсила .docx файлларидан барча ҳадисларни чиқариш (v2).

v2 ўзгариш: бир неча ҳадислар бирлаштирилган форматлар:
  - "299, 300, 301. <rowi>:" — вергулли рўйхат
  - "896-897. <rowi>:" — диапазон
Кейин ҳар бир матн параграфи (»-да тугагандаги) кейинги ID га тегишли.

Юритиш:
  py parse_docx_silsila.py

Чиқиш: silsila_index.json — {hadis_id_str: {"file": ..., "rowi": ..., "matn": ..., "izoh": ...}}
"""
import os
import re
import json
import sys
import glob

from docx import Document

DOCX_DIR = "buxoriy kitoblari"
OUT = "silsila_index.json"

HADIS_HEADER_RE = re.compile(
    r"^\s*(\d+(?:\s*[,–—\-]\s*\d+)*)\s*[.\-–—]\s*(.+?)\s*$"
)
ID_LIST_RE = re.compile(r"\d+")
BOB_RE = re.compile(r"^\s*\d+\s*[-­–—­\s]*[БB][ОO][БB]", re.IGNORECASE)


def get_lines(path):
    doc = Document(path)
    lines = []
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for ln in cell.text.split("\n"):
                    lines.append(ln)
    return lines


def expand_id_spec(spec):
    """`299, 300, 301` ёки `896-897` ёки `1156-1157-1158` ёки `123` ни рўйхатга ўгириш.

    Кўп тире (`A-B-C`) — кетма-кет ID лар деб қаралади (диапазон эмас).
    Икки тире (`A-B`) — диапазон сифатида қаралади.
    """
    spec = spec.strip()
    if "," in spec:
        ids = []
        for part in spec.split(","):
            part = part.strip()
            if "-" in part or "–" in part or "—" in part:
                ids.extend(expand_id_spec(part))
            else:
                ids.append(int(part))
        return ids
    if "-" in spec or "–" in spec or "—" in spec:
        parts = [p.strip() for p in re.split(r"[\-–—]", spec) if p.strip()]
        if len(parts) == 2:
            a, b = int(parts[0]), int(parts[1])
            return list(range(a, b + 1))
        if len(parts) >= 3:
            # Multiple dashes — treat each as separate ID (e.g., 1156-1157-1158)
            return [int(p) for p in parts]
    return [int(spec)]


def split_body_by_closures(body_lines):
    """Body қаторларни ҳадис гуруҳларига ажратиш.

    Қоида: қатор `»` билан тугаса (баъзан кейин `.` ёки `, дедилар.` каби)
    шу ердан кейин янги гуруҳ бошланади.
    """
    groups = []
    current = []
    for ln in body_lines:
        ls = ln.strip()
        if not ls:
            continue
        # Izoh blokk — alohida tutiladi
        if ls.startswith("*Изоҳ") or ls.startswith("* Изоҳ") or ls.startswith("Изоҳ:"):
            # ёпиш бўлмаган бўлса, илова
            current.append(ls)
            continue
        # variantlar: Б), В), А) — alternativ tarjima — joriy hadisga qo'shilsin
        if re.match(r"^[А-ЯA-Z]\)\s+", ls):
            current.append(ls)
            continue
        current.append(ls)
        # Closure detect: ends with » or »followed by punctuation/word
        stripped = ls.rstrip().rstrip(".").rstrip()
        # Look at last 30 chars for closing »
        tail = stripped[-50:]
        if "»" in tail:
            # find last »
            last_close = stripped.rfind("»")
            after = stripped[last_close + 1:].strip()
            # accept if after is empty or short word like 'дедилар', 'деди', 'дейилди'
            if not after or re.match(r"^[,\.]?\s*(дедилар|деди|дейилди|дейишди|дедим)?\s*\.?\s*$", after):
                groups.append(current)
                current = []
    if current:
        groups.append(current)
    return groups


def parse_one(path):
    """Битта docx файлдан ҳадислар луғатини чиқариш."""
    lines = get_lines(path)
    res = {}
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i].strip()
        m = HADIS_HEADER_RE.match(ln)
        if not m:
            i += 1
            continue
        id_spec = m.group(1)
        after_header = m.group(2)
        # Handle `1997. 1998.` pattern — peel off additional leading IDs
        while True:
            m2 = re.match(r"^\s*(\d+)\s*[.\-–—]\s*(.*)$", after_header)
            if not m2:
                break
            next_id = int(m2.group(1))
            if 0 < next_id < 8000 and len(m2.group(2)) > 10:
                id_spec = id_spec + ", " + str(next_id)
                after_header = m2.group(2)
            else:
                break
        try:
            ids = expand_id_spec(id_spec)
        except (ValueError, Exception):
            i += 1
            continue
        if not ids or any(idn <= 0 or idn > 8000 for idn in ids):
            i += 1
            continue
        rowi_line = after_header  # may be rowi (ends with :) or matn
        # collect body lines until next hadis header or BOB heading
        body = []
        j = i + 1
        while j < n:
            nxt = lines[j].strip()
            if HADIS_HEADER_RE.match(nxt):
                break
            if BOB_RE.match(nxt):
                break
            body.append(nxt)
            j += 1

        # Determine rowi: if after_header ends with ':' or has no «», take as rowi
        rowi = ""
        if rowi_line.startswith("«"):
            # No separate rowi line — matn starts immediately
            body = [rowi_line] + body
        elif rowi_line.endswith(":") or (
            "«" not in rowi_line and ":" not in rowi_line[-3:] and len(rowi_line) < 200
        ):
            rowi = rowi_line.rstrip(":").strip()
        else:
            body = [rowi_line] + body

        # Extract izoh blocks (anywhere in body)
        izoh_parts = []
        matn_body_lines = []
        for b in body:
            bs = b.strip()
            if not bs:
                continue
            if bs.startswith("*Изоҳ:") or bs.startswith("* Изоҳ:") or bs.startswith("Изоҳ:"):
                izoh_parts.append(re.sub(r"^\*?\s*Изоҳ\s*:\s*", "", bs))
            else:
                matn_body_lines.append(b)

        # Split matn lines into groups based on closures
        groups = split_body_by_closures(matn_body_lines)

        # Build results per ID
        n_ids = len(ids)
        n_groups = len(groups)
        for k, hno in enumerate(ids):
            # Pick which group(s) to associate
            if n_groups == 0:
                matn = ""
            elif n_groups == 1:
                # one group for all IDs — REPLICATE (parallel narration)
                matn = "\n\n".join(groups[0])
            elif n_groups == n_ids:
                matn = "\n\n".join(groups[k])
            elif n_groups < n_ids:
                # fewer groups than IDs — replicate last available group
                gi = min(k, n_groups - 1)
                matn = "\n\n".join(groups[gi])
            else:  # more groups than IDs
                if k < n_ids - 1:
                    matn = "\n\n".join(groups[k])
                else:
                    # last ID gets the remaining groups merged
                    matn = "\n\n".join(["\n\n".join(g) for g in groups[k:]])

            # Post-process: if matn empty but rowi looks like a narrative
            # (long sentence, ends with period/full stop), swap into matn
            r = rowi
            m = matn.strip()
            if not m and r and (len(r) > 80 or r.rstrip().endswith(".")):
                m = r
                r = ""

            entry = {
                "rowi": r,
                "matn": m,
                "izoh": "\n\n".join(izoh_parts).strip() if k == 0 else "",
                "id_group": id_spec,
                "group_idx": k,
                "group_total": n_ids,
            }
            res[hno] = entry
        i = j
    return res


def main():
    files = sorted(glob.glob(os.path.join(DOCX_DIR, "*.docx")))
    print(f"Файллар: {len(files)}")
    index = {}
    for path in files:
        name = os.path.basename(path)
        try:
            data = parse_one(path)
        except Exception as e:
            print(f"  XATO: {name}: {e}")
            continue
        for hno, ent in data.items():
            key = str(hno)
            if key in index:
                if not isinstance(index[key], list):
                    index[key] = [index[key]]
                index[key].append({**ent, "file": name})
            else:
                index[key] = {**ent, "file": name}
        print(f"  {name}: {len(data)} ҳадис")
    print(f"Жами уник ID: {len(index)}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"Ёзилди: {OUT}")
    nums = [int(k) for k in index.keys()]
    if nums:
        print(f"ID диапазон: {min(nums)} .. {max(nums)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
