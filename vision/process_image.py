from extract_tiles import TileExtractor
import pytesseract
import cv2
import numpy as np
import os
import shutil
from concurrent.futures import ThreadPoolExecutor


class ImageProcessor:
    """Detects Scrabble tiles, classifies each letter with Tesseract OCR,
    and outputs an annotated image."""

    # Minimum % of genuinely dark pixels (< INK_THRESHOLD) in center to consider
    # the tile "has a letter".  Uses a fixed threshold, NOT Otsu, so blank tiles
    # with uniform noise don't get split into fake "black" pixels.
    BLACK_PIXEL_THRESH = 0.02
    INK_THRESHOLD = 140  # pixel values below this are considered "ink"

    # Below this confidence, treat as unrecognised
    CONFIDENCE_THRESH = 20  # Tesseract confidence is 0-100

    def __init__(self, camera_config="camera.yaml"):
        self.extractor = TileExtractor(camera_config)
        print("ImageProcessor ready (using Tesseract OCR)")

    # ── Geometry ─────────────────────────────────────────────────────

    @staticmethod
    def _order_points(pts):
        s = pts.sum(axis=1)
        d = np.diff(pts, axis=1)
        tl, br = pts[np.argmin(s)], pts[np.argmax(s)]
        tr, bl = pts[np.argmin(d)], pts[np.argmax(d)]
        return np.array([tl, tr, br, bl], dtype=np.float32)

    # ── Crop ─────────────────────────────────────────────────────────

    @staticmethod
    def _remove_black_rim(crop, depth_threshold=0.2, black_threshold=None):
        """Remove black pixels from the rim unless they connect to content
        that extends more than depth_threshold (e.g., 20%) into the image.
        
        Args:
            crop: Grayscale image
            depth_threshold: Fraction of image depth (0.0-1.0) that content must reach
            black_threshold: Pixel value below which is considered "black"
        
        Returns:
            Cropped image with black rim removed
        """
        if black_threshold is None:
            black_threshold = ImageProcessor.INK_THRESHOLD
        
        h, w = crop.shape
        depth_pixels = int(min(h, w) * depth_threshold)
        
        # Identify black pixels
        black_mask = (crop < black_threshold).astype(np.uint8)
        
        # Use connected components to find all black regions
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            black_mask, connectivity=8
        )
        
        # Create mask: 1 for pixels to keep, 0 for pixels to remove
        keep_mask = np.ones((h, w), dtype=np.uint8)
        
        # Check each connected component
        for label_id in range(1, num_labels):  # Skip background (label 0)
            # Get all pixels in this component
            component_mask = (labels == label_id)
            component_y, component_x = np.where(component_mask)
            
            if len(component_y) == 0:
                continue
            
            # Check if this component touches any edge
            touches_edge = (
                np.any(component_y == 0) or  # top edge
                np.any(component_y == h - 1) or  # bottom edge
                np.any(component_x == 0) or  # left edge
                np.any(component_x == w - 1)  # right edge
            )
            
            if not touches_edge:
                # Component doesn't touch edge, keep it
                continue
            
            # Component touches edge - check if it extends deep enough
            # Calculate minimum distance from any edge
            min_dist_from_top = np.min(component_y)
            min_dist_from_bottom = h - 1 - np.max(component_y)
            min_dist_from_left = np.min(component_x)
            min_dist_from_right = w - 1 - np.max(component_x)
            
            min_dist_from_edge = min(
                min_dist_from_top,
                min_dist_from_bottom,
                min_dist_from_left,
                min_dist_from_right
            )
            
            # If component doesn't reach deep enough, mark for removal
            if min_dist_from_edge < depth_pixels:
                keep_mask[component_mask] = 0
        
        # Apply mask: set removed pixels to white (background)
        result = crop.copy()
        result[keep_mask == 0] = 255
        
        return result

    @staticmethod
    def _crop_tile(gray, rect, pad=6):
        """Warp a rotated rect into an upright square crop."""
        src_pts = cv2.boxPoints(rect).astype(np.float32)
        src_pts = ImageProcessor._order_points(src_pts)

        size = int(max(rect[1])) + pad * 2
        dst_pts = np.array(
            [[pad, pad], [size - pad, pad],
             [size - pad, size - pad], [pad, size - pad]],
            dtype=np.float32,
        )
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        crop = cv2.warpPerspective(gray, M, (size, size))

        # Remove black rim unless it connects to content >20% deep
        crop = ImageProcessor._remove_black_rim(crop, depth_threshold=0.2)
        
        # Trim bottom 15% to avoid tile border artifacts
        h = crop.shape[0]
        inner = crop[0:int(h * 0.85), :]

        inner = cv2.resize(inner, (80, 80), interpolation=cv2.INTER_CUBIC)

        # White buffer so letter is never clipped
        inner = cv2.copyMakeBorder(
            inner, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255
        )
        return inner

    # ── Blank detection ──────────────────────────────────────────────

    @staticmethod
    def _is_blank(crop):
        """Quick check: count genuinely dark pixels in the CENTER of the crop.
        Uses a fixed brightness threshold so blank tiles with uniform noise
        don't get falsely classified as having a letter."""
        h, w = crop.shape[:2]
        # Only look at the center 50 % of the crop
        y0, y1 = h // 4, 3 * h // 4
        x0, x1 = w // 4, 3 * w // 4
        center = crop[y0:y1, x0:x1]

        # Count pixels darker than INK_THRESHOLD (actual ink, not Otsu noise)
        dark_ratio = np.sum(center < ImageProcessor.INK_THRESHOLD) / center.size
        return dark_ratio < ImageProcessor.BLACK_PIXEL_THRESH

    # ── Bimodal thresholding ─────────────────────────────────────────

    def _find_bimodal_threshold(gray):
        # Otsu as baseline
        t_otsu, _ = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # percentile guard
        lo, hi = np.percentile(gray, (5, 95))
        # Raise baseline white by adding offset and adjusting upper bound
        t = int(np.clip(t_otsu - 50, lo + 10, hi - 10))
        return t


    # ── Tesseract single-character recognition ─────────────────────

    TESS_CONFIG = "--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    @staticmethod
    def _make_variants(gray):
        """Return multiple preprocessed versions of a crop so that
        different letter shapes each get a variant that works well."""
        h, w = gray.shape
        variants = []

        # v0: raw grayscale at original size (works for most letters)
        variants.append(gray)

        # v1: Otsu-binarised, upscaled 3× (helps O, T, H, round shapes)
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        up_bin = cv2.resize(binary, (w * 3, h * 3),
                            interpolation=cv2.INTER_CUBIC)
        variants.append(up_bin)

        # v2: Otsu-binarised + dilate dark strokes, upscaled 3× (helps I, Q)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        dilated = cv2.erode(binary, kernel, iterations=1)  # erode white = thicken black
        up_dil = cv2.resize(dilated, (w * 3, h * 3),
                            interpolation=cv2.INTER_CUBIC)
        variants.append(up_dil)

        return variants

    @staticmethod
    def _tesseract_one(img):
        """Run Tesseract on a single image.
        Returns (letter_or_None, confidence)."""
        try:
            data = pytesseract.image_to_data(
                img, config=ImageProcessor.TESS_CONFIG,
                output_type=pytesseract.Output.DICT,
            )
        except pytesseract.TesseractError:
            return None, -1

        best_letter, best_conf = None, -1
        for text, conf in zip(data["text"], data["conf"]):
            conf = int(conf)
            text = text.strip()
            if len(text) == 1 and text.isalpha() and conf > best_conf:
                best_letter = text.upper()
                best_conf = conf

        # Fallback: image_to_string sometimes returns a letter that
        # image_to_data missed
        if best_letter is None:
            try:
                raw = pytesseract.image_to_string(
                    img, config=ImageProcessor.TESS_CONFIG
                ).strip()
                if len(raw) == 1 and raw.isalpha():
                    best_letter = raw.upper()
                    best_conf = 0
            except pytesseract.TesseractError:
                pass

        return best_letter, best_conf

    @staticmethod
    def _recognize_char(crop):
        """Try multiple preprocessing variants × 4 rotations, return
        (letter_or_None, confidence) for the best result."""
        variants = ImageProcessor._make_variants(crop)
        best_letter, best_conf = None, -1
        for variant in variants:
            for k in range(4):
                rotated = variant if k == 0 else np.rot90(variant, k)
                letter, conf = ImageProcessor._tesseract_one(rotated)
                if letter is not None and conf > best_conf:
                    best_letter = letter
                    best_conf = conf
        return best_letter, best_conf

    # ── Parallel preprocessing ───────────────────────────────────────

    @staticmethod
    def _preprocess_one(gray, rect, idx, crop_dir):
        """Crop tile, check blank, save crop + binarised images.
        Returns (idx, rect, crop, is_blank)."""
        crop = ImageProcessor._crop_tile(gray, rect)
        blank = ImageProcessor._is_blank(crop)

        crop_path = os.path.join(crop_dir, f"tile_{idx:03d}.png")
        cv2.imwrite(crop_path, crop)

        # Save binarised variants for reference
        # Find bimodal threshold: detect two peaks in histogram and split at the valley
        threshold = ImageProcessor._find_bimodal_threshold(crop)
        # White background (> threshold) → white (255), dark letters (< threshold) → black (0)
        # _, binary = cv2.threshold(crop, threshold, 255, cv2.THRESH_BINARY)
        # cv2.imwrite(os.path.join(crop_dir, f"tile_{idx:03d}_bin.png"), binary)

        # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        # dilated = cv2.erode(binary, kernel, iterations=1)
        # cv2.imwrite(os.path.join(crop_dir, f"tile_{idx:03d}_dil.png"), dilated)

        return idx, rect, crop, blank

    # ── Drawing ──────────────────────────────────────────────────────

    @staticmethod
    def _draw_results(gray, results):
        """Draw bounding boxes on the image.
        Each result is (rect, letter, status) where status is
        'recognised', 'blank', or 'unknown'."""
        output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        for rect, letter, status in results:
            box = cv2.boxPoints(rect).astype(np.int32)
            if status == "recognised":
                color = (0, 255, 0)       # green
            elif status == "blank":
                color = (255, 0, 0)       # blue
            else:  # unknown
                color = (0, 165, 255)     # orange
            cv2.drawContours(output, [box], 0, color, 2)
            if letter:
                cx, cy = int(rect[0][0]), int(rect[0][1])
                cv2.putText(output, letter, (cx - 10, cy + 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return output

    # ── Public API ───────────────────────────────────────────────────

    def process(self, output_path="output_boxes.jpg", crop_dir="crops-07"):
        # Prepare crop directory
        if os.path.exists(crop_dir):
            shutil.rmtree(crop_dir)
        os.makedirs(crop_dir)

        
        tiles, gray = self.extractor.extract()
        print(f"Found {len(tiles)} tiles, preprocessing...")

        # ── Step 1: parallel crop + blank check ──────────────────────
        preprocessed = []
        with ThreadPoolExecutor() as pool:
            futures = [
                pool.submit(self._preprocess_one, gray, rect, i, crop_dir)
                for i, rect in enumerate(tiles)
            ]
            for f in futures:
                preprocessed.append(f.result())

        non_blank = [(idx, rect, crop) for idx, rect, crop, blank in preprocessed if not blank]
        blank_count = len(preprocessed) - len(non_blank)
        print(f"  {blank_count} blank, {len(non_blank)} to classify")

        # ── Step 2: Tesseract OCR (multiple variants × 4 rotations) ───
        ocr_map = {}  # idx → letter
        if non_blank:
            print(f"  Running Tesseract on {len(non_blank)} tiles "
                  f"(3 variants × 4 rotations each)...")

            def _classify_tile(args):
                idx, rect, crop = args
                letter, conf = ImageProcessor._recognize_char(crop)
                if letter is not None and conf >= self.CONFIDENCE_THRESH:
                    return idx, letter
                return idx, None

            with ThreadPoolExecutor() as pool:
                for idx, letter in pool.map(_classify_tile, non_blank):
                    if letter is not None:
                        ocr_map[idx] = letter

        # ── Step 4: assemble + draw ──────────────────────────────────
        results = []
        for idx, rect, _crop, blank in preprocessed:
            if blank:
                results.append((rect, None, "blank"))
            elif idx in ocr_map:
                results.append((rect, ocr_map[idx], "recognised"))
            else:
                results.append((rect, None, "unknown"))

        n_recognised = sum(1 for *_, s in results if s == "recognised")
        n_blank = sum(1 for *_, s in results if s == "blank")
        n_unknown = sum(1 for *_, s in results if s == "unknown")
        print(f"Result: {n_recognised} letters, "
              f"{n_blank} blank, {n_unknown} unknown "
              f"out of {len(results)} tiles")

        output = self._draw_results(gray, results)
        cv2.imwrite(output_path, output)
        print(f"Saved → {output_path}")

        return results, output


if __name__ == "__main__":
    processor = ImageProcessor()
    processor.process()
