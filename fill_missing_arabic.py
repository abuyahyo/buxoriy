"""arabic.json'га ҳозирча йўқ бўлган ҳадислар учун арабчасини ar_source'дан қўшиш.

Орқа фон:
  - 70 та ҳадис arabic.json'да йўқ ва inline matn_ar'и ҳам йўқ.
  - 66 таси ar_source.json'да HID бўйича топилади (фойдаланилмаган дубликат
    каноник дубликат — h272/h273 каби бир хил арабча, лекин Мансур нашрида
    турли таржима жиҳатларини кўрсатган).
  - build_arabic.py скелет-мослаштириши уларни ишончсиз деб ташлаб қўйган.

Бу скрипт: фойдаланилмаган арабчани arabic.json'га қўшади (UI «Арабча» тугмаси
учун очиб боради).
"""
import json
import sys


def main():
    with open("data.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    with open("arabic.json", "r", encoding="utf-8") as f:
        arabic = json.load(f)
    with open("ar_source.json", "r", encoding="utf-8") as f:
        ar_src = json.load(f)

    src_by_num = {h.get("hadithnumber"): h for h in ar_src["hadiths"]}

    flat = {h["id"]: h for k in db for b in k.get("boblar", []) for h in b.get("hadislar", [])}
    missing = [hid for hid, h in flat.items() if not h.get("matn_ar", "").strip() and str(hid) not in arabic]

    added = []
    no_source = []
    for hid in missing:
        src = src_by_num.get(hid)
        text = (src.get("text", "").strip() if src else "")
        if text:
            arabic[str(hid)] = text
            added.append(hid)
        else:
            no_source.append(hid)

    with open("arabic.json", "w", encoding="utf-8") as f:
        json.dump(arabic, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Added to arabic.json: {len(added)}")
    print(f"Still no source: {len(no_source)} {no_source}")
    print(f"arabic.json now has {len(arabic)} entries")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
