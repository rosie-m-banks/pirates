#!/usr/bin/env python3
"""
Webcam feed → OpenAI Vision → backend pipeline.

Captures frames from:
  1. OAK-D camera (via DepthAI)  — if available
  2. Any regular USB / built-in webcam (via OpenCV)

Shows a live preview window.  Every INTERVAL seconds (default 5) the latest
frame is sent to the OpenAI gpt-4o Vision model, which extracts player words
and available letters.  The resulting JSON is POSTed to the backend's
/update-data endpoint for game-state processing and WebSocket broadcast.

Setup:
    pip install opencv-python numpy openai python-dotenv

    Create a  vision/.env  file:
        OPENAI_API_KEY=sk-proj-...

Usage:
    python webcam_feed.py                          # defaults
    python webcam_feed.py --interval 3             # post every 3 s
    python webcam_feed.py --backend http://host:3000
    python webcam_feed.py --camera opencv           # force regular webcam
    python webcam_feed.py --camera oak              # force OAK camera
    python webcam_feed.py --camera opencv --device 1

Press SPACE to force an immediate capture+POST.
Press 'q' to quit.
"""

import argparse
import base64
import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import cv2
import numpy as np

# Load .env (if present) before reading OPENAI_API_KEY
try:
    from dotenv import load_dotenv
    load_dotenv()  # reads vision/.env when cwd is vision/
except ImportError:
    pass  # python-dotenv not installed — user must export the var manually

from openai import OpenAI

# ── Try importing OAK camera support ─────────────────────────────────
_OAK_AVAILABLE = False
try:
    from oak import Oak
    _OAK_AVAILABLE = True
except Exception:
    pass


# ── Camera abstractions ─────────────────────────────────────────────

class OpenCVCamera:
    """Wraps cv2.VideoCapture for any standard webcam."""

    def __init__(self, device_index=0):
        self.cap = cv2.VideoCapture(device_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open webcam (index {device_index})")
        time.sleep(0.5)
        print(f"[camera] Opened OpenCV webcam (index {device_index})")

    def get_frame(self):
        ret, frame = self.cap.read()
        return frame if ret else None

    def close(self):
        self.cap.release()


class OAKCamera:
    """Wraps the OAK DepthAI camera from oak.py."""

    def __init__(self, config_path="camera.yaml"):
        self.oak = Oak(config_path)
        print("[camera] Opened OAK-D camera")

    def get_frame(self):
        gray = self.oak.get_gray()
        if gray is None:
            return None
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    def close(self):
        try:
            self.oak.close()
        except Exception:
            pass


def open_camera(preference="auto", device_index=0, oak_config="camera.yaml"):
    if preference in ("auto", "oak"):
        if _OAK_AVAILABLE:
            try:
                return OAKCamera(oak_config)
            except Exception as exc:
                if preference == "oak":
                    raise
                print(f"[camera] OAK unavailable ({exc}), falling back to OpenCV")
        elif preference == "oak":
            raise RuntimeError("depthai not installed — cannot use OAK camera")
    return OpenCVCamera(device_index)


# ── OpenAI Vision ────────────────────────────────────────────────────

VISION_PROMPT = """\
You are analysing a photograph of a word / tile board game called "Pirates".

Look at the image carefully and extract:
1. The words each player currently has on their board, grouped by player.
   - If you cannot tell which words belong to which player, put them all under one player.
   - Each word should be lowercase letters only.
2. The pool of available (unused) letter tiles visible in the image.
   - Return them as a single lowercase string (e.g. "abeglmr").

Return **ONLY** valid JSON in exactly this schema:

{
  "players": [
    { "words": ["word1", "word2"] },
    { "words": ["word3"] }
  ],
  "availableLetters": "abcdefg"
}

Rules:
- All letters lowercase a-z.
- If a word is partially obscured, make your best guess.
- If no available letters are visible, set "availableLetters" to "".
- Do NOT include any text outside the JSON object.\
"""


def frame_to_base64(frame: np.ndarray, jpeg_quality: int = 85) -> str:
    """JPEG-encode a BGR frame and return a base64 string."""
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def call_openai_vision(client: OpenAI, b64_image: str) -> dict:
    """Send a base64 JPEG to gpt-4o and return the parsed game-data dict."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=1024,
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    game_data = json.loads(raw)

    # Normalise: accept both { players } and { wordsPerPlayer }
    if "wordsPerPlayer" in game_data and "players" not in game_data:
        game_data["players"] = [{"words": w} for w in game_data["wordsPerPlayer"]]
        del game_data["wordsPerPlayer"]
    game_data.setdefault("availableLetters", "")

    return game_data


# ── Post to backend ──────────────────────────────────────────────────

def post_game_data(backend_url: str, game_data: dict):
    """POST the extracted game data JSON to /update-data.

    Returns the parsed JSON response dict, or None on error.
    """
    payload = json.dumps(game_data).encode("utf-8")
    url = backend_url.rstrip("/") + "/update-data"
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        print(f"[post] HTTP {exc.code}: {err_body[:300]}")
    except URLError as exc:
        print(f"[post] Connection error: {exc.reason}")
    except Exception as exc:
        print(f"[post] {exc}")
    return None


# ── Main loop ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Webcam → OpenAI Vision → backend")
    parser.add_argument("--backend", default="http://localhost:3000",
                        help="Backend base URL (default: http://localhost:3000)")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Seconds between automatic captures (default: 5)")
    parser.add_argument("--camera", choices=["auto", "oak", "opencv"], default="auto",
                        help="Camera preference (default: auto)")
    parser.add_argument("--device", type=int, default=0,
                        help="OpenCV webcam device index (default: 0)")
    parser.add_argument("--jpeg-quality", type=int, default=85,
                        help="JPEG quality 1-100 (default: 85)")
    parser.add_argument("--no-preview", action="store_true",
                        help="Disable the live preview window")
    args = parser.parse_args()

    # ── Validate API key ─────────────────────────────────────────────
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.")
        print("  Create a  vision/.env  file with:")
        print("    OPENAI_API_KEY=sk-proj-...")
        print("  Or export it in your shell before running this script.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    print(f"[main] OpenAI key loaded (…{api_key[-4:]})")
    print(f"[main] Backend: {args.backend}")
    print(f"[main] Capture interval: {args.interval}s")

    # ── Open camera ──────────────────────────────────────────────────
    cam = open_camera(args.camera, args.device)

    last_post = 0.0
    frame_count = 0
    fps_start = time.time()
    status_text = "Waiting for first capture..."
    status_color = (0, 255, 255)  # yellow

    print("[main] Starting — press SPACE to force capture, 'q' to quit.\n")

    try:
        while True:
            frame = cam.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            frame_count += 1
            now = time.time()

            # ── Overlay HUD ──────────────────────────────────────────
            display = frame.copy()
            elapsed_since_post = now - last_post if last_post else args.interval
            countdown = max(0, args.interval - elapsed_since_post)
            fps = frame_count / (now - fps_start) if (now - fps_start) > 0 else 0

            cv2.putText(display, f"FPS: {fps:.1f}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(display, f"Next capture in: {countdown:.1f}s",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 255, 255), 2)
            cv2.putText(display, status_text, (10, 85),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)

            if not args.no_preview:
                cv2.imshow("Pirates - Webcam Feed", display)

            # ── Keyboard ─────────────────────────────────────────────
            key = cv2.waitKey(1) & 0xFF
            force = key == ord(" ")
            if key == ord("q"):
                break

            # ── Periodic capture → Vision → POST ─────────────────────
            if force or (now - last_post >= args.interval):
                print(f"[capture] Encoding frame & calling OpenAI Vision...")
                status_text = "Calling OpenAI Vision..."
                status_color = (0, 255, 255)

                try:
                    b64 = frame_to_base64(frame, args.jpeg_quality)
                    game_data = call_openai_vision(client, b64)

                    players = game_data.get("players", [])
                    letters = game_data.get("availableLetters", "")
                    word_summary = ", ".join(
                        " ".join(p.get("words", [])) for p in players
                    )
                    print(f"[vision]  Players' words: [{word_summary}]")
                    print(f"[vision]  Available letters: {letters}")

                    # POST to backend
                    print(f"[post]   Sending to {args.backend}/update-data ...")
                    resp = post_game_data(args.backend, game_data)
                    if resp and resp.get("ok"):
                        print(f"[post]   Broadcast to {resp.get('broadcast', '?')} client(s)")
                        status_text = f"OK — words: [{word_summary}]  letters: {letters}"
                        status_color = (0, 255, 0)
                    else:
                        print("[post]   Backend returned error (see above)")
                        status_text = "Backend error"
                        status_color = (0, 0, 255)

                except Exception as exc:
                    print(f"[error]  {exc}")
                    status_text = f"Error: {exc}"
                    status_color = (0, 0, 255)

                last_post = time.time()
                print()

    except KeyboardInterrupt:
        print("\nInterrupted — shutting down.")

    cam.close()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
