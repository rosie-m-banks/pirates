"""Build letter templates (A.png through Z.png) from real Bananagram tile crops.

Run process_image.py once to fill vision/crops/ with tile images, then run this
script. For each crop you'll be asked for the letter (A-Z) or Enter to skip.
Saves to vision/templates/ so the main pipeline can recognize tiles consistently.

Usage:
  cd vision
  python build_templates.py [crops_dir]

If crops_dir is omitted, uses ./crops. If crops/ is empty, run process_image.py
first to capture tiles.
"""

import os
import sys
import cv2
import glob

try:
    import matplotlib.pyplot as plt
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CROPS_DIR = os.path.join(SCRIPT_DIR, "crops")
DEFAULT_TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")


def main():
    crops_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CROPS_DIR
    templates_dir = DEFAULT_TEMPLATES_DIR
    if not os.path.isdir(crops_dir):
        print(f"Crops directory not found: {crops_dir}")
        print("Run process_image.py first to capture tiles into vision/crops/")
        sys.exit(1)
    os.makedirs(templates_dir, exist_ok=True)

    paths = sorted(glob.glob(os.path.join(crops_dir, "*.png")))
    if not paths:
        print(f"No PNG files in {crops_dir}. Run process_image.py first.")
        sys.exit(1)
    print(f"Found {len(paths)} crops. Enter letter (A-Z) for each, or Enter to skip.")
    print("Templates will be saved to", templates_dir)

    for path in paths:
        name = os.path.basename(path)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        if HAS_PLOT:
            plt.clf()
            plt.imshow(img, cmap="gray")
            plt.title(name)
            plt.axis("off")
            plt.draw()
            plt.pause(0.01)
        letter = input(f"  {name} -> Letter (A-Z or Enter to skip): ").strip().upper()
        if not letter or len(letter) != 1 or letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            continue
        out_path = os.path.join(templates_dir, f"{letter}.png")
        cv2.imwrite(out_path, img)
        print(f"    Saved -> {out_path}")

    if HAS_PLOT:
        plt.close()
    print("Done. You can run process_image.py; it will use these templates.")


if __name__ == "__main__":
    main()
