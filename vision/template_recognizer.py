"""Template-based letter recognition for Bananagram tiles.

Uses only reference images (A.png through Z.png) from real tiles. Same
normalization for every crop and template: binarize, center the letter,
fixed size. No OCR models. Works consistently when templates are from
your actual tile set.
"""

import os
import cv2
import numpy as np

DEFAULT_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates"
)
TEMPLATE_SIZE = 64
LETTER_ROI_FRAC = 0.70  # use center 70% for letter
MIN_MATCH_SCORE = 0.45   # reject below this (TM_CCOEFF_NORMED is in [-1, 1])


def _letter_roi(img, center_frac=LETTER_ROI_FRAC):
    """Center crop to isolate letter and remove tile edges."""
    h, w = img.shape[:2]
    m = (1.0 - center_frac) / 2.0
    y0, y1 = int(h * m), int(h * (1 - m))
    x0, x1 = int(w * m), int(w * (1 - m))
    return img[y0:y1, x0:x1]


def _binarize_same_conv(roi):
    """Otsu binarize; force convention letter=black (0), background=white (255).
    If most pixels are black after Otsu, assume background was dark -> invert."""
    if roi.ndim > 2:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binary) < 127:
        binary = 255 - binary
    return binary


def _center_letter(img, size=TEMPLATE_SIZE):
    """Put the letter's centroid at the center. img: binarized, letter=black.
    Work in 'size' space so output is always size x size."""
    if img.shape[0] != size or img.shape[1] != size:
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_CUBIC)
    pts = np.column_stack(np.where(img == 0))
    if len(pts) == 0:
        return img
    cy, cx = pts.mean(axis=0)
    dx = size / 2.0 - cx
    dy = size / 2.0 - cy
    M = np.float64([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(img, M, (size, size), borderValue=255)


def normalize_for_match(img, size=TEMPLATE_SIZE):
    """Same pipeline for crop and template: ROI -> resize -> binarize -> center."""
    roi = _letter_roi(img, LETTER_ROI_FRAC)
    resized = cv2.resize(roi, (size, size), interpolation=cv2.INTER_CUBIC)
    binary = _binarize_same_conv(resized)
    return _center_letter(binary, size)


def _match_score(prep, tpl):
    """Correlation score in [0, 1]. Higher = better match."""
    r = cv2.matchTemplate(prep, tpl, cv2.TM_CCOEFF_NORMED)
    s = float(r[0, 0])
    return (s + 1.0) / 2.0


class TemplateRecognizer:
    """Match tile crops to A–Z templates. Templates must be normalized the same way."""

    def __init__(self, template_dir=None):
        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        self._templates = []  # list of (letter, normalized 64x64 uint8)
        self._load_templates()

    def _load_templates(self):
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            path = os.path.join(self.template_dir, f"{letter}.png")
            if not os.path.isfile(path):
                continue
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            normalized = normalize_for_match(img, TEMPLATE_SIZE)
            self._templates.append((letter, normalized))
        if self._templates:
            print(f"TemplateRecognizer: loaded {len(self._templates)} templates from {self.template_dir}")
        else:
            print(f"TemplateRecognizer: no templates in {self.template_dir}. Run build_templates.py first.")

    @property
    def available(self):
        return len(self._templates) > 0

    def recognize(self, crop):
        """Return (letter_or_None, confidence_0_100). Uses 4 rotations and both polarities."""
        if not self._templates:
            return None, 0.0
        prep = normalize_for_match(crop, TEMPLATE_SIZE)
        best_letter, best_score = None, -1.0
        # Try 4 rotations and both polarities (letter black vs letter white)
        for k in range(4):
            rot = prep if k == 0 else np.rot90(prep, k)
            for img in (rot, 255 - rot):
                for letter, tpl in self._templates:
                    score = _match_score(img, tpl)
                    if score > best_score:
                        best_score = score
                        best_letter = letter
        if best_score < MIN_MATCH_SCORE:
            return None, 0.0
        conf = min(100.0, best_score * 100.0)
        return best_letter, conf

    def predict_batch(self, crops):
        """Return list of (letter_or_None, confidence_0_100) for each crop."""
        return [self.recognize(c) for c in crops]
