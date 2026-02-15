#!/usr/bin/env python3
"""Live tile viewer – grabs frames from the OAK camera, detects and classifies
Scrabble tiles in real time, and displays an annotated video feed in an OpenCV
window.

Usage:
    python live_tile_viewer.py

Press 'q' in the viewer window to quit.
"""

import time
import cv2
import numpy as np

from oak import Oak
from extract_tiles import TileExtractor
from tile_character_extractor import (
    load_reference_images,
    crop_tile,
    normalize,
    classify_tile,
    is_blank,
)

# ── Annotation colours (BGR) ─────────────────────────────────────────
COLOR_MATCHED = (0, 255, 0)      # green  – confidently matched letter
COLOR_BLANK   = (255, 0, 0)      # blue   – blank / no ink
COLOR_UNKNOWN = (0, 165, 255)    # orange – ambiguous match
COLOR_LABEL   = (0, 0, 255)      # red    – letter text


def annotate_frame(gray, tiles, references):
    """Classify every detected tile and draw boxes + labels on a BGR copy.

    Returns:
        output  – annotated BGR image (numpy array)
        letters – list of detected letter strings (may include duplicates)
    """
    output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    letters = []

    for rect in tiles:
        tile_crop = crop_tile(gray, rect)
        box = cv2.boxPoints(rect).astype(np.int32)

        # Blank tile – draw blue box, skip classification
        if is_blank(tile_crop):
            cv2.drawContours(output, [box], 0, COLOR_BLANK, 2)
            continue

        # Classify
        crop_norm = normalize(tile_crop)
        letter, mse = classify_tile(crop_norm, references)

        if letter:
            color = COLOR_MATCHED
            letters.append(letter)
        else:
            color = COLOR_UNKNOWN

        cv2.drawContours(output, [box], 0, color, 2)

        # Draw letter label at tile centre
        if letter:
            cx, cy = int(rect[0][0]), int(rect[0][1])
            cv2.putText(
                output, letter, (cx - 10, cy + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_LABEL, 2,
            )

    return output, letters


def main():
    # ── One-time setup ────────────────────────────────────────────────
    print("Initialising OAK camera...")
    oak = Oak("camera.yaml")

    print("Loading reference images (this may take a moment)...")
    references = load_reference_images()
    if not references:
        print("ERROR: No reference images found – classification will be skipped.")

    print("Starting live viewer – press 'q' to quit.\n")

    frame_count = 0
    fps_start = time.time()

    # ── Main loop ─────────────────────────────────────────────────────
    try:
        while True:
            gray = oak.get_gray()
            if gray is None:
                # Camera not ready yet – wait a bit and retry
                time.sleep(0.01)
                continue

            # Detect tiles
            tiles = TileExtractor._detect_tiles(gray)

            # Classify + annotate
            if references:
                output, letters = annotate_frame(gray, tiles, references)
            else:
                # No references loaded – just draw bounding boxes
                output = TileExtractor._draw_boxes(gray, tiles)
                letters = []

            # Overlay FPS counter
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed > 0:
                fps = frame_count / elapsed
                cv2.putText(
                    output, f"FPS: {fps:.1f}  Tiles: {len(tiles)}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
                )

            # Show letters summary at the bottom
            if letters:
                summary = "Letters: " + " ".join(letters)
                h = output.shape[0]
                cv2.putText(
                    output, summary, (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
                )

            # Display
            cv2.imshow("Tile Viewer", output)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("\nInterrupted – shutting down.")

    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
