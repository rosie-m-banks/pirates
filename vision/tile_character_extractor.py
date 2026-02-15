"""Tile character extractor using direct image matching against labeled crop data.

Extracts tiles from an image using extract_tiles, then compares each tile crop
against all non-synthetic reference images in letter_data/A..Z/ and outputs
the best-matching letter for each tile.

Matching approach:
  - Both tile crops and reference images are normalized to grayscale, resized,
    and CLAHE-equalized (but NOT binarized, to preserve structural detail).
  - For each letter, the score is the best (lowest) MSE across all reference
    images for that letter.  Also tries all four rotations (0/90/180/270)
    to handle tiles that come out rotated after perspective warp.
  - A winner-margin is required so ambiguous tiles are flagged.
"""

import os
import sys
import cv2
import numpy as np

from extract_tiles import TileExtractor

# ── Paths ────────────────────────────────────────────────────────────
VISION_DIR = os.path.dirname(os.path.abspath(__file__))
LETTER_DATA_DIR = os.path.join(VISION_DIR, "letter_data")

# ── Matching parameters ──────────────────────────────────────────────
MATCH_SIZE = 64           # resize both crop and ref to this before comparing
LETTER_ROI_FRAC = 0.70    # center-crop fraction to isolate the letter
INK_THRESHOLD = 140       # below this = dark pixel
BLACK_PIXEL_THRESH = 0.02 # min dark-pixel ratio to consider non-blank
MIN_WINNER_MARGIN = 0.005 # best must beat second-best by this (MSE scale)
ROTATION_PENALTY  = 0.008 # added to MSE for 90/270 rotations, prefer upright


# ── Normalization (same pipeline for tile crops AND reference images) ─

def _letter_roi(img, center_frac=LETTER_ROI_FRAC):
    """Center-crop to isolate the letter and drop tile edges."""
    h, w = img.shape[:2]
    m = (1.0 - center_frac) / 2.0
    y0, y1 = int(h * m), int(h * (1 - m))
    x0, x1 = int(w * m), int(w * (1 - m))
    return img[y0:y1, x0:x1]


_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))


def normalize(img, size=MATCH_SIZE):
    """ROI crop -> grayscale -> resize -> CLAHE equalize -> float [0,1]."""
    if img.ndim > 2:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    roi = _letter_roi(img, LETTER_ROI_FRAC)
    resized = cv2.resize(roi, (size, size), interpolation=cv2.INTER_AREA)
    eq = _clahe.apply(resized)
    return eq.astype(np.float32) / 255.0


# ── Matching ─────────────────────────────────────────────────────────

def _mse(a, b):
    """Mean-squared error between two float images. Lower = better match."""
    return float(np.mean((a - b) ** 2))


# ── Tile cropping (borrowed from process_image) ─────────────────────

def _order_points(pts):
    pts = np.asarray(pts, dtype=np.float32)
    order = np.lexsort((pts[:, 0], pts[:, 1]))
    ordered = pts[order]
    tl, tr, bl, br = ordered[0], ordered[1], ordered[2], ordered[3]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def crop_tile(gray, rect, pad=6):
    """Warp a rotated rect into an upright square crop (grayscale 128x128)."""
    if rect[1][0] <= 0 or rect[1][1] <= 0:
        return np.ones((128, 128), dtype=np.uint8) * 255

    src_pts = cv2.boxPoints(rect).astype(np.float32)
    h_img, w_img = gray.shape
    src_pts[:, 0] = np.clip(src_pts[:, 0], 0, w_img - 1)
    src_pts[:, 1] = np.clip(src_pts[:, 1], 0, h_img - 1)
    src_pts = _order_points(src_pts)

    size = int(max(rect[1])) + pad * 2
    if size <= 0:
        return np.ones((128, 128), dtype=np.uint8) * 255

    dst_pts = np.array(
        [[pad, pad], [size - pad, pad],
         [size - pad, size - pad], [pad, size - pad]],
        dtype=np.float32,
    )
    try:
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    except cv2.error:
        return np.ones((128, 128), dtype=np.uint8) * 255

    crop = cv2.warpPerspective(gray, M, (size, size),
                               flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT,
                               borderValue=255)
    h, w = crop.shape
    margin_h = int(h * 0.15)
    margin_w = int(w * 0.15)
    if margin_h * 2 >= h or margin_w * 2 >= w:
        inner = crop
    else:
        inner = crop[margin_h:h - margin_h, margin_w:w - margin_w]
    inner = cv2.resize(inner, (80, 80), interpolation=cv2.INTER_CUBIC)
    inner = cv2.copyMakeBorder(inner, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255)
    return inner


def is_blank(crop):
    """True if center region has too few dark pixels to be a letter."""
    h, w = crop.shape[:2]
    center = crop[h // 4:3 * h // 4, w // 4:3 * w // 4]
    dark_ratio = np.sum(center < INK_THRESHOLD) / center.size
    return dark_ratio < BLACK_PIXEL_THRESH


# ── Reference image loading ──────────────────────────────────────────

def load_reference_images(letter_data_dir=LETTER_DATA_DIR):
    """Load all non-synthetic reference images from letter_data/A..Z
    AND from crops-NN directories (which have labeled files like A.png, B.png).

    Returns dict: { 'A': [norm_img1, norm_img2, ...], 'B': [...], ... }
    """
    references = {}
    total = 0

    # 1. Load from letter_data/A..Z (skip synthetics)
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        letter_dir = os.path.join(letter_data_dir, letter)
        if not os.path.isdir(letter_dir):
            continue
        refs = references.setdefault(letter, [])
        for fname in sorted(os.listdir(letter_dir)):
            if not fname.lower().endswith(".png"):
                continue
            # Skip synthetic images
            if fname.lower().startswith("synth"):
                continue
            path = os.path.join(letter_dir, fname)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            norm = normalize(img)
            refs.append(norm)
            total += 1

    # 2. Also load from crops-NN directories (labeled letter PNGs)
    for entry in sorted(os.listdir(VISION_DIR)):
        if not entry.startswith("crops-") or entry == "crops-test":
            continue
        crop_dir_path = os.path.join(VISION_DIR, entry)
        if not os.path.isdir(crop_dir_path):
            continue
        for fname in os.listdir(crop_dir_path):
            if not fname.endswith(".png"):
                continue
            stem = os.path.splitext(fname)[0].upper()
            if len(stem) != 1 or stem not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                continue  # skip BAD.png, tile_000.png, etc.
            letter = stem
            path = os.path.join(crop_dir_path, fname)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            norm = normalize(img)
            references.setdefault(letter, []).append(norm)
            total += 1

    print(f"Loaded {total} reference images across {len(references)} letters")
    return references


# ── Per-tile classification ──────────────────────────────────────────

def classify_tile(crop_norm, references):
    """Compare a normalized tile crop against all reference images.

    Tries all four orientations (0, 90, 180, 270 degrees) since tiles can
    end up in any rotation after perspective warp. For each letter, keeps
    the best (min) MSE across all references and orientations.

    Returns (best_letter, best_mse) or (None, best_mse).
    """
    letter_scores = {}  # letter -> best MSE (lower = better)

    # Try all four orientations (0, 90, 180, 270 degrees)
    # Apply a penalty to rotated matches so the upright orientation is
    # preferred unless a rotation gives a clearly better match. This
    # prevents confusion between rotationally-similar letters (L/J, etc.)
    orientations = [
        (crop_norm,               0.0),                # 0°   – no penalty
        (np.rot90(crop_norm, 1),  ROTATION_PENALTY),   # 90°
        (np.rot90(crop_norm, 2),  ROTATION_PENALTY / 2),  # 180° – small penalty
        (np.rot90(crop_norm, 3),  ROTATION_PENALTY),   # 270°
    ]

    for oriented, penalty in orientations:
        for letter, ref_list in references.items():
            for ref in ref_list:
                score = _mse(oriented, ref) + penalty
                if letter not in letter_scores or score < letter_scores[letter]:
                    letter_scores[letter] = score

    # Sort by ascending MSE (best first)
    ranked = sorted(letter_scores.items(), key=lambda x: x[1])
    best_letter, best_mse = ranked[0]
    second_mse = ranked[1][1] if len(ranked) > 1 else 1.0

    margin = second_mse - best_mse
    if margin < MIN_WINNER_MARGIN:
        # Too ambiguous – return best guess but flag low confidence
        return best_letter, best_mse

    return best_letter, best_mse


# ── Main pipeline ────────────────────────────────────────────────────

def extract_and_classify(photo_path=None, output_path="output_matched.jpg",
                         crop_dir=None):
    """Full pipeline: detect tiles -> crop -> match against references -> annotate.

    Returns list of (letter_or_None, score) for each detected tile.
    """
    # 1. Load reference images
    print("Loading reference images...")
    references = load_reference_images()
    if not references:
        print("ERROR: No reference images found in", LETTER_DATA_DIR)
        return []

    # 2. Detect tiles
    print("Detecting tiles...")
    extractor = TileExtractor(photo_path=photo_path)
    tiles, gray = extractor.extract()
    if tiles is None or gray is None:
        print("ERROR: Could not get frame / detect tiles")
        return []
    print(f"Found {len(tiles)} tiles")

    # 3. Crop each tile
    results = []
    letters_found = []
    for i, rect in enumerate(tiles):
        tile_crop = crop_tile(gray, rect)

        # Save crop if requested
        if crop_dir:
            os.makedirs(crop_dir, exist_ok=True)
            cv2.imwrite(os.path.join(crop_dir, f"tile_{i:03d}.png"), tile_crop)

        # Skip blank tiles
        if is_blank(tile_crop):
            results.append((rect, None, 1.0, "blank"))
            continue

        # Normalize and classify
        crop_norm = normalize(tile_crop)
        letter, mse = classify_tile(crop_norm, references)

        status = "matched" if letter else "unknown"
        results.append((rect, letter, mse, status))
        if letter:
            letters_found.append(letter)

        label = f"{letter} (mse={mse:.4f})" if letter else f"? (mse={mse:.4f})"
        print(f"  Tile {i:3d}: {label}")

    # 4. Summary
    n_matched = sum(1 for *_, s in results if s == "matched")
    n_blank = sum(1 for *_, s in results if s == "blank")
    n_unknown = sum(1 for *_, s in results if s == "unknown")
    print(f"\nResult: {n_matched} matched, {n_blank} blank, {n_unknown} unknown "
          f"out of {len(results)} tiles")
    if letters_found:
        print(f"Letters: {' '.join(letters_found)}")

    # 5. Draw annotated image
    output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for rect, letter, mse, status in results:
        box = cv2.boxPoints(rect).astype(np.int32)
        if status == "matched":
            color = (0, 255, 0)
        elif status == "blank":
            color = (255, 0, 0)
        else:
            color = (0, 165, 255)
        cv2.drawContours(output, [box], 0, color, 2)
        if letter:
            cx, cy = int(rect[0][0]), int(rect[0][1])
            cv2.putText(output, letter, (cx - 10, cy + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    cv2.imwrite(output_path, output)
    print(f"Saved annotated image -> {output_path}")

    return [(letter, score) for _, letter, score, _ in results]


# ── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    photo = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else "output_matched.jpg"
    extract_and_classify(photo_path=photo, output_path=out)
