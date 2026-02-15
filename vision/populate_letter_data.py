"""Copy crops into letter_data/A, B, ..., Z by labeling each image. Run after process_image.py."""

import os
import shutil
import glob
import cv2

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    HAS_PLOT = True
except Exception:
    HAS_PLOT = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CROPS_DIR = os.path.join(SCRIPT_DIR, "crops")
LETTER_DATA_DIR = os.path.join(SCRIPT_DIR, "letter_data")


def main():
    crops_dir = DEFAULT_CROPS_DIR
    if not os.path.isdir(crops_dir):
        print(f"No crops dir: {crops_dir}. Run process_image.py first.")
        return 1
    os.makedirs(LETTER_DATA_DIR, exist_ok=True)
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        os.makedirs(os.path.join(LETTER_DATA_DIR, c), exist_ok=True)

    paths = sorted(glob.glob(os.path.join(crops_dir, "*.png")))
    if not paths:
        print(f"No PNGs in {crops_dir}.")
        return 1
    print(f"Found {len(paths)} crops. Enter letter (A-Z) to copy into letter_data/<Letter>/, or Enter to skip.")
    copied = 0
    for path in paths:
        name = os.path.basename(path)
        img = None
        if HAS_PLOT:
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                plt.clf()
                plt.imshow(img, cmap="gray")
                plt.title(name)
                plt.axis("off")
                plt.draw()
                plt.pause(0.01)
        letter = input(f"  {name} -> Letter (A-Z or Enter to skip): ").strip().upper()
        if not letter or len(letter) != 1 or letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            continue
        dest_dir = os.path.join(LETTER_DATA_DIR, letter)
        base, ext = os.path.splitext(name)
        dest = os.path.join(dest_dir, f"{base}{ext}")
        if os.path.exists(dest):
            i = 1
            while os.path.exists(os.path.join(dest_dir, f"{base}_{i}{ext}")):
                i += 1
            dest = os.path.join(dest_dir, f"{base}_{i}{ext}")
        shutil.copy2(path, dest)
        copied += 1
        print(f"    -> {dest}")
    if HAS_PLOT:
        plt.close()
    print(f"Done. Copied {copied} images. Run train_letter_model.py to train.")


if __name__ == "__main__":
    raise SystemExit(main() or 0)
