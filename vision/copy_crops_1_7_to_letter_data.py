"""Copy letter images from crops-01 .. crops-07 into letter_data/[Letter]/batch_NN.png."""

import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LETTER_DATA = os.path.join(SCRIPT_DIR, "letter_data")
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def main():
    for batch in range(1, 8):
        src_dir = os.path.join(SCRIPT_DIR, f"crops-{batch:02d}")
        if not os.path.isdir(src_dir):
            continue
        for letter in LETTERS:
            src = os.path.join(src_dir, f"{letter}.png")
            if not os.path.isfile(src):
                continue
            dest_dir = os.path.join(LETTER_DATA, letter)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, f"batch_{batch:02d}.png")
            shutil.copy2(src, dest)
            print(f"  {letter}.png (crops-{batch:02d}) -> letter_data/{letter}/batch_{batch:02d}.png")
    print("Done.")

if __name__ == "__main__":
    main()
