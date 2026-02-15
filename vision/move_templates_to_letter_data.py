"""One-off: move templates/A.png..Z.png into letter_data/A/..Z/ for training."""

import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
LETTER_DATA_DIR = os.path.join(SCRIPT_DIR, "letter_data")

def main():
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        src = os.path.join(TEMPLATES_DIR, f"{letter}.png")
        if not os.path.isfile(src):
            continue
        os.makedirs(os.path.join(LETTER_DATA_DIR, letter), exist_ok=True)
        dest = os.path.join(LETTER_DATA_DIR, letter, f"{letter}.png")
        shutil.move(src, dest)
        print(f"  {letter}.png -> letter_data/{letter}/")
    print("Done. Templates moved to letter_data.")

if __name__ == "__main__":
    main()
