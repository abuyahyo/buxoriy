"""silsila_index.json дан data.json'га таржималарни кўчириш.

Юритиш:
  py apply_silsila.py            # курсатиш, ёзмасдан (dry-run)
  py apply_silsila.py --write    # ҳақиқатан ёзиш

Қоидалар:
  - Фақат `tarjima_status='missing'` ҳадисларга ёзиш (бошқаларни эҳтиёт қилиш)
  - silsila entry'да matn бўш бўлса — ўтказиб юбориш
  - rowi нинг охиридаги `:` олиб ташланади
  - matn'нинг типографик `‒`, `­` каби белгилари тозаланади
  - Қўш бўш жой тузатилади
"""
import json
import re
import sys
import argparse


def clean_text(s):
    if not s:
        return s
    # Normalize various dashes to em-dash for narration patterns
    s = s.replace("‒", "—").replace("­", "")  # figure dash → em dash, soft hyphen removed
    # Two consecutive spaces → one
    s = re.sub(r" {2,}", " ", s)
    # Remove non-breaking space oddities
    s = s.replace(" ", " ")
    s = s.replace("​", "")
    return s.strip()


def clean_rowi(s):
    s = clean_text(s)
    s = s.rstrip(":").strip()
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--include-translated", action="store_true",
                    help="also overwrite hadiths already translated (e.g., 4 pilots)")
    args = ap.parse_args()

    with open("silsila_index.json", "r", encoding="utf-8") as f:
        idx = json.load(f)
    with open("data.json", "r", encoding="utf-8") as f:
        db = json.load(f)

    applied = []
    skipped_empty = []
    skipped_already = []
    not_in_index = []

    for k in db:
        for b in k.get("boblar", []):
            for h in b.get("hadislar", []):
                status = h.get("tarjima_status")
                if status != "missing" and not args.include_translated:
                    continue
                key = str(h["id"])
                if key not in idx:
                    if status == "missing":
                        not_in_index.append(h["id"])
                    continue
                ent = idx[key]
                if isinstance(ent, list):
                    ent = ent[0]
                matn = clean_text(ent.get("matn", ""))
                rowi = clean_rowi(ent.get("rowi", ""))
                izoh = clean_text(ent.get("izoh", ""))
                if not matn.strip():
                    skipped_empty.append(h["id"])
                    continue
                # If overwriting existing pilot, save backup
                h["matn"] = matn
                if rowi:
                    h["rowi"] = rowi
                if izoh:
                    h["izoh"] = izoh
                h["tarjima_status"] = "translated"
                applied.append(h["id"])

    print(f"Applied:        {len(applied)}")
    print(f"Skipped (empty matn in silsila): {len(skipped_empty)}")
    print(f"Not in silsila index:            {len(not_in_index)}")
    print()
    if skipped_empty:
        print(f"empty matn ids (first 20): {skipped_empty[:20]}")
    if not_in_index:
        print(f"not in index (first 20):   {not_in_index[:20]}")

    if args.write:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, separators=(",", ":"))
        print(f"\\ndata.json ёзилди.")
    else:
        print("\\n(dry run — --write билан юритинг ҳақиқатан ёзиш учун)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
