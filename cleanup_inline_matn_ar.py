"""data.json'дан фойдаланилмайдиган inline matn_ar ни олиб ташлаш.

Аввал 272 та таржимасиз ҳадис учун "таржимаси йўқ" stub'ни кўрсатиш керак эди.
Энди ҳаммаси таржимали + arabic.json'да арабчаси бор → inline matn_ar кераксиз.

Шу билан data.json ~270 КБ камаяди.

Олиб ташланадигани: arabic.json'да HID бор бўлса, h['matn_ar'] олиб ташланади.
Сақланадигани: arabic.json'да бўлмаган ҳадислар учун matn_ar inline қолади (агар бор бўлса).
"""
import json
import sys


def main():
    with open("data.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    with open("arabic.json", "r", encoding="utf-8") as f:
        arabic = json.load(f)

    removed = 0
    kept = 0
    for k in db:
        for b in k.get("boblar", []):
            for h in b.get("hadislar", []):
                if not h.get("matn_ar", "").strip():
                    continue
                if str(h["id"]) in arabic:
                    del h["matn_ar"]
                    removed += 1
                else:
                    kept += 1

    # Also clean up tarjima_status — no longer needed since matn is always present
    cleaned_status = 0
    for k in db:
        for b in k.get("boblar", []):
            for h in b.get("hadislar", []):
                if "tarjima_status" in h:
                    del h["tarjima_status"]
                    cleaned_status += 1
                if "canon_no" in h and h["canon_no"] == h["id"]:
                    # canon_no = id (default) is redundant
                    del h["canon_no"]

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Removed inline matn_ar: {removed}")
    print(f"Kept inline matn_ar (not in arabic.json): {kept}")
    print(f"Removed tarjima_status entries: {cleaned_status}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
