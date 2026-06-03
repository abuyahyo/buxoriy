"""Batch screenshot search: clears field, types ID, scrolls, captures multiple screenshots per hadith."""
import sys, subprocess, time, os

ADB = r"C:\Users\abu_y\AppData\Local\Android\Sdk\platform-tools\adb.exe"
OUT_DIR = r"C:\Users\abu_y\buxoriy\apk_extract\app_shots"

os.makedirs(OUT_DIR, exist_ok=True)


def adb(*args):
    return subprocess.run([ADB] + list(args), capture_output=True, text=True)


def screencap(path):
    res = subprocess.run([ADB, "exec-out", "screencap", "-p"], stdout=subprocess.PIPE)
    with open(path, "wb") as f:
        f.write(res.stdout)


def process_id(hid):
    # Clear search field with multiple backspaces
    for _ in range(6):
        adb("shell", "input", "keyevent", "67")
    time.sleep(0.3)
    # Type ID
    adb("shell", "input", "text", str(hid))
    time.sleep(2.5)
    # Close keyboard
    adb("shell", "input", "keyevent", "4")
    time.sleep(0.5)
    # Top of result
    screencap(os.path.join(OUT_DIR, f"h{hid}_a.png"))
    # Scroll
    adb("shell", "input", "swipe", "540", "1700", "540", "500", "500")
    time.sleep(0.5)
    screencap(os.path.join(OUT_DIR, f"h{hid}_b.png"))
    # Scroll more
    adb("shell", "input", "swipe", "540", "1700", "540", "500", "500")
    time.sleep(0.5)
    screencap(os.path.join(OUT_DIR, f"h{hid}_c.png"))


def main():
    ids = sys.argv[1:]
    for hid in ids:
        print(f"Processing {hid}...")
        process_id(hid)
    print("Done.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
