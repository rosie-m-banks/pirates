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
TEMPLATE_SIZE = 96   # larger = more discriminative (was 64)
LETTER_ROI_FRAC = 0.70
MIN_MATCH_SCORE = 0.52   # reject weak matches
# Winner must beat second-best by this much (stops "everything is O")
MIN_WINNER_MARGIN = 0.07


def _letter_roi(img, center_frac=LETTER_ROI_FRAC):
    """Center crop to isolate letter and remove tile edges."""
    h, w = img.shape[:2]
    m = (1.0 - center_frac) / 2.0
    y0, y1 = int(h * m), int(h * (1 - m))
    x0, x1 = int(w * m), int(w * (1 - m))
    return img[y0:y1, x0:x1]


def _binarize_same_conv(roi):
    """Binarize; letter=black (0), background=white (255). Use adaptive then
    enforce convention so template and crop are comparable."""
    if roi.ndim > 2:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    h, w = roi.shape[:2]
    block = min(31, (min(h, w) // 4) | 1)
    binary = cv2.adaptiveThreshold(
        roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block, 8
    )
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
        """Return (letter_or_None, confidence_0_100). Uses 4 rotations and both polarities.
        Only accepts when one template clearly wins (margin over second-best)."""
        if not self._templates:
            return None, 0.0
        prep = normalize_for_match(crop, TEMPLATE_SIZE)
        # For each candidate (rotation, polarity), get best letter and score; require clear winner
        best_letter, best_score = None, -1.0
        for k in range(4):
            rot = prep if k == 0 else np.rot90(prep, k)
            for img in (rot, 255 - rot):
                scores = [(_match_score(img, tpl), letter) for letter, tpl in self._templates]
                scores.sort(key=lambda x: -x[0])
                first_score, first_letter = scores[0]
                second_score = scores[1][0] if len(scores) > 1 else 0.0
                margin_ok = (first_score - second_score) >= MIN_WINNER_MARGIN
                if (first_score >= MIN_MATCH_SCORE and margin_ok and first_score > best_score):
                    best_score = first_score
                    best_letter = first_letter
        if best_letter is None:
            return None, 0.0
        conf = min(100.0, best_score * 100.0)
        return best_letter, conf

    def predict_batch(self, crops):
        """Return list of (letter_or_None, confidence_0_100) for each crop."""
        return [self.recognize(c) for c in crops]
