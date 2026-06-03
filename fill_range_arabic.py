"""Canonical Bukhari range-hadis IDs учун arabic.json'га арабчасини range-leader'дан копия.

Орқа фон: канон Бухорий рақамлашда баъзи иснодлар жуфт/учлик ID га эга
(масалан 5709-5712 битта ҳадис, ё 6173-6175 битта ҳадис). Sunnah.com бу range
шаклида кўрсатади. ar_source.json'нинг ўзи фақат range-leader (биринчи ID)да
матн беради, қолганлари бўш.

Бу скрипт data.json'да бор лекин arabic.json'да йўқ ID лар учун, range-leader
матнини нусхалайди.

Sunnah.com'дан тасдиқлангани:
  5712 part of 5709-5712 range → leader h5709
  5774, 5775 part of 5773-5775 range → leader h5773
  6175 part of 6173-6175 range → leader h6173
"""
import json
import sys

RANGE_LEADERS = {
    5712: 5709,
    5774: 5773,
    5775: 5773,
    6175: 6173,
}


def main():
    with open("arabic.json", "r", encoding="utf-8") as f:
        arabic = json.load(f)

    added = []
    for tid, leader in RANGE_LEADERS.items():
        leader_text = arabic.get(str(leader))
        if not leader_text:
            print(f"  warn: h{leader} not in arabic.json")
            continue
        if str(tid) in arabic:
            print(f"  skip: h{tid} already in arabic.json")
            continue
        arabic[str(tid)] = leader_text
        added.append(tid)

    with open("arabic.json", "w", encoding="utf-8") as f:
        json.dump(arabic, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Added: {len(added)} — {added}")
    print(f"arabic.json now: {len(arabic)} entries")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
