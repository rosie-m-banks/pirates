"""Generate synthetic letter data from letter_data with augmentations.

Reads images from letter_data/A, B, ..., Z (only non-synthetic originals),
applies random translations, rotations, blur, noise/dots, and brightness/contrast,
and saves new images into the same folders with a synth_ prefix so the trainer
uses both original and synthetic data.

Usage (from vision/):
  python augment_synthetic_data.py [--data ./letter_data] [--per-image 8] [--seed 42]
"""

import os
import argparse
import random
import numpy as np
import cv2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(SCRIPT_DIR, "letter_data")
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SYNTH_PREFIX = "synth_"
IMAGE_EXTS = (".png", ".jpg", ".jpeg")


def _is_synthetic(filename):
    return os.path.basename(filename).lower().startswith(SYNTH_PREFIX)


def _augment_translate(img, max_frac=0.12, fill=255):
    h, w = img.shape[:2]
    tx = random.randint(-int(w * max_frac), int(w * max_frac))
    ty = random.randint(-int(h * max_frac), int(h * max_frac))
    M = np.float32([[1, 0, tx], [0, 1, ty]])
    return cv2.warpAffine(img, M, (w, h), borderValue=fill)


def _augment_rotate(img, max_deg=18, fill=255):
    h, w = img.shape[:2]
    angle = random.uniform(-max_deg, max_deg)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), borderValue=fill)


def _augment_blur(img, max_sigma=1.2):
    k = random.choice([3, 5])
    sigma = random.uniform(0.3, max_sigma)
    return cv2.GaussianBlur(img, (k, k), sigma)


def _augment_dots(img, num_dots=None, dot_value_range=(0, 255)):
    out = img.copy()
    h, w = out.shape[:2]
    if num_dots is None:
        num_dots = random.randint(2, max(3, (h * w) // 800))
    for _ in range(num_dots):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        v = random.choice([random.randint(*dot_value_range), 255])
        r = random.randint(1, 2)
        cv2.circle(out, (x, y), r, int(v), -1)
    return out


def _augment_brightness_contrast(img, brightness_range=(-40, 40), contrast_range=(0.85, 1.2)):
    b = random.randint(*brightness_range)
    c = random.uniform(*contrast_range)
    out = img.astype(np.float32) * c + b
    return np.clip(out, 0, 255).astype(np.uint8)


def _augment_scale(img, scale_range=(0.92, 1.08), fill=255):
    h, w = img.shape[:2]
    s = random.uniform(*scale_range)
    new_w, new_h = int(w * s), int(h * s)
    if new_w <= 0 or new_h <= 0:
        return img
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    pad_l = (w - new_w) // 2
    pad_t = (h - new_h) // 2
    # If scaled up, resized is larger than (h,w); crop to fit. If scaled down, pad.
    src_l = max(0, -pad_l)
    src_t = max(0, -pad_t)
    src_r = min(new_w, w - pad_l)
    src_b = min(new_h, h - pad_t)
    dst_l = max(0, pad_l)
    dst_t = max(0, pad_t)
    dst_r = min(w, pad_l + new_w)
    dst_b = min(h, pad_t + new_h)
    out = np.full((h, w), fill, dtype=img.dtype)
    out[dst_t:dst_b, dst_l:dst_r] = resized[src_t:src_b, src_l:src_r]
    return out


def _augment_slight_noise(img, sigma=8):
    noise = np.random.randn(*img.shape).astype(np.float32) * sigma
    out = img.astype(np.float32) + noise
    return np.clip(out, 0, 255).astype(np.uint8)


def augment_once(img, rng_state=None):
    if rng_state is not None:
        random.setstate(rng_state)
    # Ensure 2D grayscale for consistent ops
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Apply a random subset of augmentations (order can vary)
    ops = [
        _augment_translate,
        _augment_rotate,
        _augment_blur,
        _augment_dots,
        _augment_brightness_contrast,
        _augment_scale,
        _augment_slight_noise,
    ]
    n_apply = random.randint(2, min(5, len(ops)))
    chosen = random.sample(ops, n_apply)
    for op in chosen:
        img = op(img)
    return img


def collect_originals(data_dir):
    """Return dict letter -> list of paths to non-synthetic images."""
    originals = {}
    for letter in LETTERS:
        folder = os.path.join(data_dir, letter)
        if not os.path.isdir(folder):
            continue
        paths = []
        for name in os.listdir(folder):
            if _is_synthetic(name):
                continue
            if any(name.lower().endswith(ext) for ext in IMAGE_EXTS):
                paths.append(os.path.join(folder, name))
        if paths:
            originals[letter] = paths
    return originals


def main():
    ap = argparse.ArgumentParser(
        description="Generate synthetic letter data from letter_data with augmentations."
    )
    ap.add_argument(
        "--data",
        default=DEFAULT_DATA_DIR,
        help="Root dir with subdirs A, B, ..., Z",
    )
    ap.add_argument(
        "--per-image",
        type=int,
        default=8,
        help="Number of synthetic variants to generate per original image",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be generated",
    )
    args = ap.parse_args()

    if not os.path.isdir(args.data):
        print(f"Data dir not found: {args.data}")
        return 1

    random.seed(args.seed)
    np.random.seed(args.seed)

    originals = collect_originals(args.data)
    if not originals:
        print("No original (non-synth) images found in letter_data/A..Z.")
        return 1

    total_originals = sum(len(p) for p in originals.values())
    total_synth = total_originals * args.per_image
    print(f"Found {total_originals} original images across {len(originals)} letters.")
    print(f"Will generate {args.per_image} variants each -> {total_synth} synthetic images.")
    if args.dry_run:
        for letter, paths in sorted(originals.items()):
            print(f"  {letter}: {len(paths)} originals -> {len(paths) * args.per_image} synth")
        return 0

    saved = 0
    for letter, paths in sorted(originals.items()):
        folder = os.path.join(args.data, letter)
        os.makedirs(folder, exist_ok=True)
        for i, src_path in enumerate(paths):
            base_name = os.path.splitext(os.path.basename(src_path))[0]
            img = cv2.imread(src_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                img = cv2.imread(src_path)
                if img is not None and len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if img is None:
                print(f"  Skip (unreadable): {src_path}")
                continue
            for j in range(args.per_image):
                rng = random.getstate()
                aug = augment_once(img, rng_state=rng)
                out_name = f"{SYNTH_PREFIX}{base_name}_{i:02d}_{j:02d}.png"
                out_path = os.path.join(folder, out_name)
                cv2.imwrite(out_path, aug)
                saved += 1
        print(f"  {letter}: {len(paths)} originals -> {len(paths) * args.per_image} synth written")
    print(f"Done. Wrote {saved} synthetic images to {args.data}")


if __name__ == "__main__":
    raise SystemExit(main() or 0)
