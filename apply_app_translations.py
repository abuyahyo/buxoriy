"""Olin Silsila app skreenshot'idan кўлда чиқарилган таржималарни data.json'га ёзиш.

Юритиш:
  py apply_app_translations.py
"""
import json
import sys

TRANSLATIONS = {
    # h6154 (k78 Адаб китоби, 91-БОБ — Мушрикларни ҳажв қилиш ҳақида)
    # Олтин Силсилада тушириб қолдирилган. Менинг таржимам (Арабчадан).
    6154: {
        "rowi": "Ибн Умар розияллоҳу анҳумодан ривоят қилинади",
        "matn": "«Набий соллаллоҳу алайҳи васаллам: «Бирортангизнинг ичи йиринг билан тўлиб кетиши, шеър билан тўлиб кетишидан кўра яхшидир», дедилар».",
    },
    # h6155 (k78 Адаб китоби, 93-БОБ — Набий соллаллоҳу алайҳи васалламнинг «Қўлинг тупроққа қорилгур...»)
    # Аввалги ҳадиснинг параллел занжири, Абу Ҳурайрадан.
    6155: {
        "rowi": "Абу Ҳурайра розияллоҳу анҳудан ривоят қилинади",
        "matn": "«Расулуллоҳ соллаллоҳу алайҳи васаллам: «Бирор кишининг ичи (зарар берадиган) йиринг билан тўлиб кетиши, шеър билан тўлиб кетишидан яхшироқдир», дедилар».",
    },
}


def main():
    with open("data.json", "r", encoding="utf-8") as f:
        db = json.load(f)

    applied = []
    for k in db:
        for b in k.get("boblar", []):
            for h in b.get("hadislar", []):
                if h["id"] in TRANSLATIONS:
                    tr = TRANSLATIONS[h["id"]]
                    if h.get("tarjima_status") != "missing":
                        print(f"  warn: h{h['id']} already translated, skipping")
                        continue
                    h["matn"] = tr["matn"]
                    h["rowi"] = tr["rowi"]
                    if tr.get("izoh"):
                        h["izoh"] = tr["izoh"]
                    h["tarjima_status"] = "translated"
                    applied.append(h["id"])

    if applied:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Tarjima qilindi: {len(applied)} ta — {applied}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
