"""Olin Silsila app'da битта ҳадис ID сини қидириб, скриншот олиш.

Юритиш:
  py app_search.py <hadis_id>

Олдин app очиқ ва Сахихул Бухорий китоблари рўйхатида бўлсин.
"""
import sys
import subprocess
import time
import os

ADB = r"C:\Users\abu_y\AppData\Local\Android\Sdk\platform-tools\adb.exe"
OUT_DIR = r"C:\Users\abu_y\buxoriy\apk_extract"


def adb(*args):
    return subprocess.run([ADB] + list(args), capture_output=True, text=True)


def main():
    if len(sys.argv) < 2:
        print("Usage: py app_search.py <hadis_id> [<id2> ...]")
        return
    for hid in sys.argv[1:]:
        # Tap search icon (1017, 209)
        adb("shell", "input", "tap", "1017", "209")
        time.sleep(1.5)
        # Type hadith ID
        adb("shell", "input", "text", hid)
        time.sleep(1.5)
        # Close keyboard
        adb("shell", "input", "keyevent", "4")
        time.sleep(0.5)
        # Tap first result (around 540, 500)
        adb("shell", "input", "tap", "540", "500")
        time.sleep(2)
        # Screenshot
        out = os.path.join(OUT_DIR, f"h{hid}.png")
        with open(out, "wb") as f:
            res = subprocess.run([ADB, "exec-out", "screencap", "-p"], stdout=subprocess.PIPE)
            f.write(res.stdout)
        print(f"h{hid}: {out}")
        # Go back twice to return to books list
        adb("shell", "input", "keyevent", "4")
        time.sleep(0.5)
        adb("shell", "input", "keyevent", "4")
        time.sleep(0.5)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
