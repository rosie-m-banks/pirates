"""Detect Bananagram tiles and read letters. Prefers LeNet (train_lenet_letter), then LetterCNN, TrOCR, then templates."""

from extract_tiles import TileExtractor
import cv2
import numpy as np
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

from template_recognizer import TemplateRecognizer

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from letter_model import LetterRecognizer as TrOCRLetterRecognizer
    _LETTER_MODEL_AVAILABLE = True
except Exception:
    TrOCRLetterRecognizer = None
    _LETTER_MODEL_AVAILABLE = False

try:
    from lenet_letter import LeNetLetterRecognizer, DEFAULT_MODEL_PATH as LENET_PATH
    _LENET_AVAILABLE = True
except Exception:
    LeNetLetterRecognizer = None
    LENET_PATH = None
    _LENET_AVAILABLE = False

try:
    from letter_cnn import LetterCNNRecognizer, DEFAULT_MODEL_PATH as LETTER_CNN_PATH
    _LETTER_CNN_AVAILABLE = True
except Exception:
    LetterCNNRecognizer = None
    LETTER_CNN_PATH = None
    _LETTER_CNN_AVAILABLE = False


class ImageProcessor:
    """Detects tiles, classifies letters with CNN (if trained) or template matching."""

    BLACK_PIXEL_THRESH = 0.02
    INK_THRESHOLD = 140

    def __init__(self, camera_config="camera.yaml", photo_path=None, use_cnn=True):
        self.extractor = TileExtractor(camera_config, photo_path=photo_path)
        self.recognizer = None
        if use_cnn:
            # Prefer LeNet (train_lenet_letter.py), then LetterCNN, then TrOCR
            if _LENET_AVAILABLE and LENET_PATH and os.path.isfile(LENET_PATH):
                try:
                    self.recognizer = LeNetLetterRecognizer()
                    print("ImageProcessor ready (LeNet)")
                except Exception as e:
                    print(f"LeNet load failed: {e}")
            if self.recognizer is None and _LETTER_CNN_AVAILABLE and LETTER_CNN_PATH and os.path.isfile(LETTER_CNN_PATH):
                try:
                    self.recognizer = LetterCNNRecognizer()
                    print("ImageProcessor ready (LetterCNN from train_letter_model)")
                except Exception as e:
                    print(f"LetterCNN load failed: {e}")
            if self.recognizer is None and _LETTER_MODEL_AVAILABLE:
                try:
                    self.recognizer = TrOCRLetterRecognizer()
                    print("ImageProcessor ready (letter model / TrOCR)")
                except Exception as e:
                    print(f"Letter model load failed: {e}")
        if self.recognizer is None:
            self.recognizer = TemplateRecognizer()
            if not self.recognizer.available:
                print(
                    "No CNN model and no templates. Train: populate vision/letter_data/A..Z and run "
                    "train_lenet_letter.py or train_letter_model.py. Or add templates via build_templates.py."
                )
            else:
                print("ImageProcessor ready (template matching)")

    @staticmethod
    def _order_points(pts):
        """Order box points as [tl, tr, br, bl] for perspective warp."""
        pts = np.asarray(pts, dtype=np.float32)
        order = np.lexsort((pts[:, 0], pts[:, 1]))
        ordered = pts[order]
        tl, tr, bl, br = ordered[0], ordered[1], ordered[2], ordered[3]
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
        # Validate rect dimensions
        if rect[1][0] <= 0 or rect[1][1] <= 0:
            # Invalid rect, return a small white image
            return np.ones((128, 128), dtype=np.uint8) * 255
        
        src_pts = cv2.boxPoints(rect).astype(np.float32)
        
        # Validate source points are within image bounds
        h_img, w_img = gray.shape
        if np.any(src_pts < 0) or np.any(src_pts[:, 0] >= w_img) or np.any(src_pts[:, 1] >= h_img):
            # Points outside bounds, clip them
            src_pts[:, 0] = np.clip(src_pts[:, 0], 0, w_img - 1)
            src_pts[:, 1] = np.clip(src_pts[:, 1], 0, h_img - 1)
        
        src_pts = ImageProcessor._order_points(src_pts)
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
        h, w = crop.shape[0], crop.shape[1]
        margin_h = int(h * 0.15)
        margin_w = int(w * 0.15)
        if margin_h * 2 >= h or margin_w * 2 >= w:
            inner = crop
        else:
            inner = crop[margin_h:h - margin_h, margin_w:w - margin_w]
        inner = cv2.resize(inner, (80, 80), interpolation=cv2.INTER_CUBIC)

        # White buffer so letter is never clipped
        inner = cv2.copyMakeBorder(
            inner, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255
        )
        return inner

    @staticmethod
    def _is_blank(crop):
        """True if center has too few dark pixels to be a letter."""
        h, w = crop.shape[:2]
        y0, y1 = h // 4, 3 * h // 4
        x0, x1 = w // 4, 3 * w // 4
        center = crop[y0:y1, x0:x1]
        dark_ratio = np.sum(center < ImageProcessor.INK_THRESHOLD) / center.size
        return dark_ratio < ImageProcessor.BLACK_PIXEL_THRESH

    # ── Bimodal thresholding ─────────────────────────────────────────

    @staticmethod
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
        if pytesseract is None:
            return None, -1
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
        """Crop tile, check blank, save crop. Returns (idx, rect, crop, is_blank)."""
        crop = ImageProcessor._crop_tile(gray, rect)
        blank = ImageProcessor._is_blank(crop)
        crop_path = os.path.join(crop_dir, f"tile_{idx:03d}.png")
        if len(crop.shape) == 2:
            cv2.imwrite(crop_path, crop)
        else:
            gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
            cv2.imwrite(crop_path, gray_crop)
        return idx, rect, crop, blank

    @staticmethod
    def _draw_results(gray, results):
        """Draw boxes and letters. results: list of (rect, letter, status)."""
        output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        for rect, letter, status in results:
            box = cv2.boxPoints(rect).astype(np.int32)
            if status == "recognised":
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
        return output

    # ── Public API ───────────────────────────────────────────────────

    def process(self, output_path="output_boxes.jpg", crop_dir="crops-05"):
        # Prepare crop directory
        if os.path.exists(crop_dir):
            shutil.rmtree(crop_dir)
        os.makedirs(crop_dir)

        
        tiles, gray = self.extractor.extract()
        if gray is None or tiles is None:
            raise RuntimeError("Could not get a frame from the extractor")
        print(f"Found {len(tiles)} tiles, preprocessing...")

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

        ocr_map = {}
        if non_blank and self.recognizer is not None and self.recognizer.available:
            crops = [crop for _idx, _rect, crop in non_blank]
            print(f"  Classifying {len(crops)} tiles...")
            results_list = self.recognizer.predict_batch(crops)
            for (idx, _rect, _crop), (letter, conf) in zip(non_blank, results_list):
                if letter is not None:
                    ocr_map[idx] = letter
        elif non_blank:
            print("  Skipping letter recognition (no model/templates).")

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
        print(f"Result: {n_recognised} letters, {n_blank} blank, {n_unknown} unknown out of {len(results)} tiles")

        output = self._draw_results(gray, results)
        cv2.imwrite(output_path, output)
        print(f"Saved -> {output_path}")
        return results, output


if __name__ == "__main__":
    # Parse command-line arguments
    # Usage: python3 process_image.py [crop_dir] [photo_path]
    crop_dir = sys.argv[1] if len(sys.argv) > 1 else "crops-test"
    photo_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    processor = ImageProcessor(photo_path=photo_path)
    processor.process(crop_dir=crop_dir)
