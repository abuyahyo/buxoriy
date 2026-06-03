"""Olin Silsila app пайдар-пай (predecessor) кузатуви:
Ҳар бир missing ҳадис учун app id-1 билан жуфтда кўрсатади ва матн бир хил.
Шу матнни автомат копия қиламиз.

Истисно: 6154/6155 — иккаласи ҳам missing, гуруҳда бўлиши мумкин. Алоҳида текширилади.
"""
import json
import sys


def main():
    with open("data.json", "r", encoding="utf-8") as f:
        db = json.load(f)

    flat = {h["id"]: h for k in db for b in k.get("boblar", []) for h in b.get("hadislar", [])}
    missing = [hid for hid, h in flat.items() if h.get("tarjima_status") == "missing"]

    applied = []
    skipped = []
    for hid in missing:
        if hid in (6154, 6155):
            skipped.append((hid, "special pair, handle separately"))
            continue
        pred = flat.get(hid - 1)
        if not pred or not pred.get("matn", "").strip():
            skipped.append((hid, f"predecessor h{hid-1} not translated"))
            continue
        h = flat[hid]
        h["matn"] = pred["matn"]
        h["rowi"] = pred.get("rowi", "")
        if pred.get("izoh"):
            h["izoh"] = pred["izoh"]
        h["tarjima_status"] = "translated"
        applied.append(hid)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Applied (pair copy): {len(applied)}")
    print(f"  ids: {applied}")
    if skipped:
        print(f"Skipped: {len(skipped)}")
        for hid, why in skipped:
            print(f"  h{hid}: {why}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
