"""Detect Bananagram tiles and read letters. Prefers letter model (TrOCR), then LeNet, LetterCNN, then templates."""

from extract_tiles import TileExtractor
import cv2
import numpy as np
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from template_recognizer import TemplateRecognizer

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

    def __init__(self, camera_config="camera.yaml", use_cnn=True):
        self.extractor = TileExtractor(camera_config)
        self.recognizer = None
        if use_cnn:
            if _LETTER_MODEL_AVAILABLE:
                try:
                    self.recognizer = TrOCRLetterRecognizer()
                    print("ImageProcessor ready (letter model / TrOCR)")
                except Exception as e:
                    print(f"Letter model load failed: {e}")
            if self.recognizer is None and _LENET_AVAILABLE and LENET_PATH and os.path.isfile(LENET_PATH):
                try:
                    self.recognizer = LeNetLetterRecognizer()
                    print("ImageProcessor ready (LeNet)")
                except Exception as e:
                    print(f"LeNet load failed: {e}")
            if self.recognizer is None and _LETTER_CNN_AVAILABLE and LETTER_CNN_PATH and os.path.isfile(LETTER_CNN_PATH):
                try:
                    self.recognizer = LetterCNNRecognizer()
                    print("ImageProcessor ready (LetterCNN)")
                except Exception as e:
                    print(f"LetterCNN load failed: {e}")
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

    @staticmethod
    def _crop_tile(gray, rect, pad=6):
        """Warp rotated rect to upright square crop."""
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
        margin = int(size * 0.1)
        inner = crop[margin:size - margin, margin:size - margin]
        h = inner.shape[0]
        inner = inner[0:int(h * 0.85), :]
        inner = cv2.resize(inner, (80, 80), interpolation=cv2.INTER_CUBIC)
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

    @staticmethod
    def _preprocess_one(gray, rect, idx, crop_dir):
        """Crop tile, check blank, save crop. Returns (idx, rect, crop, is_blank)."""
        crop = ImageProcessor._crop_tile(gray, rect)
        blank = ImageProcessor._is_blank(crop)
        crop_path = os.path.join(crop_dir, f"tile_{idx:03d}.png")
        cv2.imwrite(crop_path, crop)
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

    def process(self, output_path="output_boxes.jpg", crop_dir="crops"):
        if os.path.exists(crop_dir):
            shutil.rmtree(crop_dir)
        os.makedirs(crop_dir)

        frame = self.extractor.oak.get_gray()
        if frame is None:
            raise RuntimeError("Could not get a frame from the Oak camera")
        gray = frame if len(frame.shape) == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tiles = self.extractor._detect_tiles(gray)
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
    processor = ImageProcessor()
    processor.process()
