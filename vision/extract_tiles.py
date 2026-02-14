from oak import Oak
import cv2
import numpy as np


class TileExtractor:
    """Grabs a grayscale frame from the Oak camera, detects Scrabble tile
    bounding boxes, draws them on the image, and writes the result to disk."""

    def __init__(self, camera_config="camera.yaml"):
        self.oak = Oak(camera_config)

    # ── Tile detection ───────────────────────────────────────────────

    @staticmethod
    def _detect_tiles(gray):
        """Find individual Scrabble tiles via Canny edges + contour filtering.

        Returns a list of cv2 RotatedRect tuples: ((cx, cy), (w, h), angle).
        """
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 20, 75)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.dilate(edges, kernel, iterations=3)

        contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        min_area = 10000
        max_area = 40000

        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            perimeter = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.06 * perimeter, True)
            if len(approx) < 4 or len(approx) > 8:
                continue

            rect = cv2.minAreaRect(cnt)
            aspect = max(rect[1]) / (min(rect[1]) + 1e-5)
            if aspect > 1.6:
                continue

            candidates.append(rect)

        # Non-maximum suppression: drop overlapping detections
        candidates.sort(key=lambda r: r[1][0] * r[1][1], reverse=True)
        tiles = []
        for rect in candidates:
            cx, cy = rect[0]
            too_close = False
            for kept in tiles:
                kcx, kcy = kept[0]
                dist = ((cx - kcx) ** 2 + (cy - kcy) ** 2) ** 0.5
                if dist < min(kept[1]) * 0.4:
                    too_close = True
                    break
            if not too_close:
                tiles.append(rect)

        return tiles

    # ── Drawing ──────────────────────────────────────────────────────

    @staticmethod
    def _draw_boxes(gray, tiles):
        """Draw rotated bounding boxes on the image and return a BGR copy."""
        output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        for rect in tiles:
            box = cv2.boxPoints(rect).astype(np.int32)
            cv2.drawContours(output, [box], 0, (0, 255, 0), 2)

            cx, cy = int(rect[0][0]), int(rect[0][1])
            cv2.circle(output, (cx, cy), 3, (0, 0, 255), -1)

        return output

    # ── Public API ───────────────────────────────────────────────────

    def extract(self, output_path="output_tiles.jpg"):
        """Grab a frame, detect tiles, draw boxes, and save the image.

        Returns:
            tiles: list of detected RotatedRect tuples
            output: the annotated BGR image (numpy array)
        """
        frame = self.oak.get_gray()
        if frame is None:
            raise RuntimeError("Could not get a frame from the Oak camera")

        gray = frame if len(frame.shape) == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tiles = self._detect_tiles(gray)
        output = self._draw_boxes(gray, tiles)

        cv2.imwrite(output_path, output)
        print(f"Saved {len(tiles)} tile boxes to {output_path}")

        return tiles, output


if __name__ == "__main__":
    extractor = TileExtractor()
    extractor.extract()

