#!/usr/bin/env python3
"""
Tile Extractor using VLM (Vision Language Model)
Extracts Bananagrams tiles from an image, segments by word and player, and identifies free letters.

Usage:
    python tile_extractor_vlm.py [image_path]
    
Click anywhere on the image to analyze it with Claude API.
"""

import os
import sys
import json
import base64
import logging
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageTk
import io
import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from anthropic import Anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Install with: pip install anthropic")
    sys.exit(1)

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    _REQUESTS_AVAILABLE = False

try:
    from oak import Oak
    _OAK_AVAILABLE = True
except ImportError:
    Oak = None
    _OAK_AVAILABLE = False
    logger.warning("Oak camera not available. Install depthai to use camera capture.")
except Exception as e:
    Oak = None
    _OAK_AVAILABLE = False
    logger.warning(f"Oak camera initialization failed: {e}")

try:
    from hand_detector import HandDetector
    _HAND_DETECTOR_AVAILABLE = True
    print("[INIT] Hand detector module imported successfully")
except ImportError as e:
    HandDetector = None
    _HAND_DETECTOR_AVAILABLE = False
    print(f"[INIT] Hand detector import failed: {e}")
    print("[INIT] Install mediapipe with: pip install mediapipe")
    logger.warning("Hand detector not available. Install mediapipe to use hand detection.")
except Exception as e:
    HandDetector = None
    _HAND_DETECTOR_AVAILABLE = False
    print(f"[INIT] Hand detector import error: {e}")
    logger.warning(f"Hand detector initialization failed: {e}")

try:
    from tile_frame_pub import TilePublisher
    _TILE_PUBLISHER_AVAILABLE = True
except ImportError as e:
    TilePublisher = None
    _TILE_PUBLISHER_AVAILABLE = False
    logger.warning(f"TilePublisher not available: {e}")
except Exception as e:
    TilePublisher = None
    _TILE_PUBLISHER_AVAILABLE = False
    logger.warning(f"TilePublisher initialization failed: {e}")


class VLMClient:
    """Client for interacting with Claude API."""
    
    def __init__(self, api_key: str):
        """Initialize Anthropic client with API key."""
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
    
    def analyze_board(self, image_path: str, max_size: int = 1024, quality: int = 85, previous_result: Optional[Dict] = None) -> Dict:
        """
        Send image to VLM and get structured analysis.
        
        Args:
            image_path: Path to image file
            max_size: Maximum dimension (width or height) for resizing (default: 1024)
            quality: JPEG quality for compression (1-100, default: 85)
            previous_result: Previous analysis result to use as baseline (optional)
        
        Returns:
            Dict with keys: 'player_words', 'free_letters'
        """
        logger.info(f"Analyzing image: {image_path}")
        
        # Read and resize/compress image before sending
        try:
            # Load image with PIL
            img = Image.open(image_path)
            original_size = img.size
            logger.debug(f"Original image size: {original_size}")
            
            # Resize if too large (maintain aspect ratio)
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {original_size} to {img.size} for faster processing")
            
            # Convert to RGB if needed (for JPEG)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to temporary bytes with compression
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=quality, optimize=True)
            img_bytes.seek(0)
            image_data = img_bytes.read()
            
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            size_mb = len(image_data) / (1024 * 1024)
            logger.info(f"Image prepared: {img.size}, {size_mb:.2f} MB, {len(image_base64)} base64 chars")
            
        except Exception as e:
            raise IOError(f"Failed to process image file: {e}")
        
        # Use JPEG format
        image_format = 'jpeg'
        
        # Build prompt with previous result if available
        prompt = """Analyze this Bananagrams board image. Extract all tiles organized by words, players, and free letters.

Instructions:
1. Identify all words (tiles connected with each other. Make sure they are real words though, otherwise add to free letters.)
2. Group words by player based on orientation/side:
   - Words on bottom left side belong to one player
   - Words on bottom right side belong to another player
   - Words on top belong to the free list
3. List free letters (not connected to any word)

"""
        
#         # Add previous result context and constraints if available
#         if previous_result:
#             previous_json = json.dumps(previous_result, indent=2)
#             prompt += f"""IMPORTANT CONSTRAINTS - Previous Board State:
# {previous_json}

# CRITICAL RULES:
# 1. The board can only change by a few letters more (not decrease) (typically 1-3 letters more. Words can completely scramble and be recombined, but the total number of letters should be within 1-5 letters of prev state if exists)
# 2. Words CANNOT lose letters - existing words can only:
#    - Have letters added to them
#    - Be rescrambled/rearranged (same letters, different order)
#    - Combine with other words and letters to form a new single word
# 3. New words can be formed from free letters or by rearranging existing words
# 4. The total number of letters should remain approximately the same (within 1-3 letters)
# 5. Use the previous state as a baseline - if a word existed before, it should still exist (possibly rearranged or recombined with another word)

# If applicable, when analyzing, compare against the previous state and ensure changes are minimal and follow these rules.

# """
        
        prompt += """Return JSON in this format only. There should be no other data sent:
{
    "player_words": {
        "player_1": [{"word": "HELLO", "tiles": ["H","E","L","L","O"]}],
        "player_2": [{"word": "WORLD", "tiles": ["W","O","R","L","D"]}]
    },
    "free_letters": ["A","B","C"]
}

Be concise. Each tile = single uppercase letter (A-Z, repeats are allowed)."""

        try:
            import time
            start_time = time.time()
            logger.info(f"Sending request to Claude API (model: {self.model})")
            
            # Make API call with timeout
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,  # Reduced from 4096 for faster response
                timeout=60.0,  # 60 second timeout
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": f"image/{image_format}",
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )
            elapsed = time.time() - start_time
            logger.info(f"API call completed in {elapsed:.2f} seconds")
            
            # Extract text from response
            response_text = message.content[0].text
            logger.debug(f"Received response from API (length: {len(response_text)})")
            
            # Save raw response for debugging
            debug_dir = Path(__file__).parent / "debug"
            debug_dir.mkdir(exist_ok=True)
            debug_file = debug_dir / f"vlm_response_{Path(image_path).stem}.txt"
            with open(debug_file, 'w') as f:
                f.write(response_text)
            logger.debug(f"Saved raw response to: {debug_file}")
            
            # Try to parse JSON from response (may be wrapped in markdown code blocks)
            json_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if json_text.startswith("```json"):
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else json_text
            elif json_text.startswith("```"):
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else json_text
            
            # Try to find JSON object in text if not at start
            if not json_text.startswith('{'):
                # Look for first { and last }
                start_idx = json_text.find('{')
                end_idx = json_text.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_text = json_text[start_idx:end_idx+1]
                    logger.debug("Extracted JSON from text")
            
            result = json.loads(json_text)
            logger.info("Successfully parsed JSON response")
            return result
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON from VLM response: {e}"
            logger.error(f"{error_msg}\nResponse preview: {response_text[:500]}")
            raise ValueError(f"{error_msg}\nFull response saved to: {debug_file}")
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}", exc_info=True)
            raise RuntimeError(f"Error calling Claude API: {e}")


class TileExtractorGUI:
    """GUI application for tile extraction using VLM."""
    
    def __init__(self, api_key: str, camera_config: str = "camera.yaml"):
        self.api_key = api_key
        self.vlm_client = VLMClient(api_key)
        self.current_image_path: Optional[str] = None
        self.current_image: Optional[Image.Image] = None
        self.photo: Optional[ImageTk.PhotoImage] = None
        self.temp_image_path: Optional[str] = None  # For camera captures
        
        # Initialize Oak camera if available
        self.oak: Optional[Oak] = None
        self.camera_config = camera_config
        if _OAK_AVAILABLE:
            try:
                logger.info(f"Initializing Oak camera from {camera_config}")
                self.oak = Oak(camera_config)
                logger.info("Oak camera initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Oak camera: {e}")
                self.oak = None
        
        # Initialize hand detector if available
        self.hand_detector: Optional[HandDetector] = None
        print(f"[INIT] _HAND_DETECTOR_AVAILABLE = {_HAND_DETECTOR_AVAILABLE}")
        if _HAND_DETECTOR_AVAILABLE:
            try:
                print("[INIT] Attempting to initialize HandDetector...")
                self.hand_detector = HandDetector()
                print("[INIT] Hand detector initialized successfully!")
                logger.info("Hand detector initialized successfully")
            except Exception as e:
                print(f"[INIT] Failed to initialize hand detector: {e}")
                logger.warning(f"Failed to initialize hand detector: {e}")
                self.hand_detector = None
        else:
            print("[INIT] Hand detector not available (import failed or not installed)")
        
        # Initialize tile publisher if available
        self.tile_publisher: Optional[TilePublisher] = None
        self.publisher_running = False
        self.publisher_thread = None
        if _TILE_PUBLISHER_AVAILABLE:
            try:
                self.tile_publisher = TilePublisher()
                logger.info("TilePublisher initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize TilePublisher: {e}")
                self.tile_publisher = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Tile Extractor - VLM")
        self.root.geometry("1200x800")
        
        # Create UI
        self._create_ui()
        
        # Load image if provided as argument
        if len(sys.argv) > 1:
            self.load_image(sys.argv[1])
    
    def _create_ui(self):
        """Create the user interface."""
        # Top frame for image display
        image_frame = tk.Frame(self.root)
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Image label with scrollable canvas
        canvas_frame = tk.Frame(image_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_v = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar_v.set)
        
        scrollbar_h = tk.Scrollbar(image_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(xscrollcommand=scrollbar_h.set)
        
        self.image_label = tk.Label(self.canvas, bg="gray")
        self.image_window_id = self.canvas.create_window(0, 0, anchor=tk.NW, window=self.image_label)
        
        # Bind click event
        self.canvas.bind("<Button-1>", self._on_image_click)
        self.image_label.bind("<Button-1>", self._on_image_click)
        
        # Instructions
        instructions = tk.Label(
            image_frame,
            text="Click anywhere on the image to analyze with VLM",
            font=("Arial", 10),
            fg="blue"
        )
        instructions.pack(pady=5)
        
        # Right frame for controls and results
        right_frame = tk.Frame(self.root, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        right_frame.pack_propagate(False)
        
        # Load image button
        load_btn = tk.Button(
            right_frame,
            text="Load Image",
            command=self._load_image_dialog,
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            padx=10,
            pady=5
        )
        load_btn.pack(pady=10, fill=tk.X)
        
        # Capture from camera button
        if self.oak is not None:
            capture_btn = tk.Button(
                right_frame,
                text="Capture from Camera",
                command=self._capture_from_camera,
                font=("Arial", 12),
                bg="#FF9800",
                fg="white",
                padx=10,
                pady=5
            )
            capture_btn.pack(pady=5, fill=tk.X)
        else:
            camera_status = tk.Label(
                right_frame,
                text="Camera not available",
                font=("Arial", 9),
                fg="gray"
            )
            camera_status.pack(pady=5)
        
        # Export results button
        self.export_btn = tk.Button(
            right_frame,
            text="Export Results (JSON)",
            command=self._export_results,
            font=("Arial", 10),
            bg="#2196F3",
            fg="white",
            padx=10,
            pady=5,
            state=tk.DISABLED
        )
        self.export_btn.pack(pady=5, fill=tk.X)
        
        # Post to backend button
        self.post_btn = tk.Button(
            right_frame,
            text="Post to Backend",
            command=self._post_to_backend,
            font=("Arial", 10),
            bg="#9C27B0",
            fg="white",
            padx=10,
            pady=5,
            state=tk.DISABLED
        )
        self.post_btn.pack(pady=5, fill=tk.X)
        
        self.last_result: Optional[Dict] = None
        self.backend_url: str = "http://localhost:3000/update-data"
        
        # Create a dedicated session for update-data requests to avoid connection interference
        # with the image publisher's requests
        if _REQUESTS_AVAILABLE:
            self.data_session = requests.Session()
            # Set connection pool size to ensure isolation
            adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1)
            self.data_session.mount('http://', adapter)
        else:
            self.data_session = None
        
        # Auto-capture state
        self.auto_capture_running = False
        self.auto_capture_timer = None
        
        # Auto-capture button
        self.auto_capture_btn = tk.Button(
            right_frame,
            text="Start Auto-Capture (15s)",
            command=self._toggle_auto_capture,
            font=("Arial", 10),
            bg="#4CAF50",
            fg="white",
            padx=10,
            pady=5
        )
        self.auto_capture_btn.pack(pady=5, fill=tk.X)
        
        # Tile publisher button
        if self.tile_publisher is not None:
            self.publisher_btn = tk.Button(
                right_frame,
                text="Start Tile Publisher (3s)",
                command=self._toggle_publisher,
                font=("Arial", 10),
                bg="#FF5722",
                fg="white",
                padx=10,
                pady=5
            )
            self.publisher_btn.pack(pady=5, fill=tk.X)
        
        # Status label
        self.status_label = tk.Label(
            right_frame,
            text="Ready. Load an image to begin.",
            font=("Arial", 10),
            wraplength=380,
            justify=tk.LEFT
        )
        self.status_label.pack(pady=5, padx=5, anchor=tk.W)
        
        # Results display
        results_label = tk.Label(
            right_frame,
            text="Results:",
            font=("Arial", 12, "bold")
        )
        results_label.pack(pady=(10, 5), anchor=tk.W)
        
        self.results_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            width=45,
            height=30,
            font=("Courier", 9)
        )
        self.results_text.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def _load_image_dialog(self):
        """Open file dialog to load an image."""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.load_image(file_path)
    
    def _validate_no_hands_multiple_frames(self, initial_frame, frame_delay=0.25, num_validation_frames=3):
        """
        Validate that no hands are detected across multiple frames.
        
        Args:
            initial_frame: The initial frame that had no hands detected
            frame_delay: Delay between frames in seconds (default: 0.25)
            num_validation_frames: Number of additional frames to check (default: 3)
        
        Returns:
            tuple: (validated_frame, all_clear) where validated_frame is the final frame
                   and all_clear is True if no hands detected in any validation frame
        """
        if self.hand_detector is None:
            # No hand detector available, skip validation
            return initial_frame, True
        
        # Check initial frame again (sanity check)
        if self.hand_detector.detect_hands(initial_frame):
            print("[VALIDATION] Initial frame now has hands, validation failed")
            return initial_frame, False
        
        # Validate across multiple frames
        validated_frame = initial_frame
        for i in range(num_validation_frames):
            print(f"[VALIDATION] Waiting {frame_delay}s before validation frame {i+1}/{num_validation_frames}...")
            time.sleep(frame_delay)
            
            # Capture new frame
            validation_frame = self.oak.get_rgb()
            if validation_frame is None:
                print(f"[VALIDATION] ERROR: Failed to capture validation frame {i+1}")
                logger.warning(f"Failed to capture validation frame {i+1}, using previous frame")
                continue
            
            # Check for hands
            has_hands = self.hand_detector.detect_hands(validation_frame)
            if has_hands:
                print(f"[VALIDATION] *** HAND DETECTED in validation frame {i+1}! Validation failed ***")
                logger.info(f"Hand detected in validation frame {i+1}, validation failed")
                return validation_frame, False
            
            # Update validated frame to the latest one
            validated_frame = validation_frame
            print(f"[VALIDATION] Validation frame {i+1}/{num_validation_frames} passed (no hands)")
        
        print(f"[VALIDATION] All {num_validation_frames} validation frames passed (no hands detected)")
        logger.info(f"All {num_validation_frames} validation frames passed (no hands detected)")
        return validated_frame, True
    
    def _capture_from_camera(self):
        """Capture a frame from the Oak camera, checking for hands and retrying if needed."""
        if self.oak is None:
            messagebox.showerror("Camera Error", "Oak camera is not available.")
            return
        
        self.status_label.config(text="Capturing frame from camera...")
        self.root.update()
        
        try:
            # Get RGB frame from camera (for hand detection)
            rgb_frame = self.oak.get_rgb()
            
            if rgb_frame is None:
                messagebox.showerror("Capture Error", "Failed to capture frame from camera.\nCamera may not be ready yet.")
                self.status_label.config(text="Camera capture failed.")
                return
            
            # Check for hands if detector is available - keep retrying until no hand is detected
            if self.hand_detector is not None:
                print("[CAPTURE] Hand detector is available, checking for hands...")
                max_retries = 100  # Safety limit to prevent infinite loop
                retry_count = 0
                
                while retry_count < max_retries:
                    print(f"[CAPTURE] Checking for hands (attempt {retry_count + 1})...")
                    has_hands = self.hand_detector.detect_hands(rgb_frame)
                    print(f"[CAPTURE] Hand detection result: {has_hands}")
                    
                    if not has_hands:
                        print("[CAPTURE] No hand detected, validating with multiple frames...")
                        logger.info("No hand detected, validating with multiple frames...")
                        self.status_label.config(text="No hand detected, validating with multiple frames...")
                        self.root.update()
                        
                        # Validate with multiple frames
                        validated_frame, all_clear = self._validate_no_hands_multiple_frames(rgb_frame)
                        rgb_frame = validated_frame
                        
                        if all_clear:
                            print("[CAPTURE] Validation passed, proceeding with capture")
                            logger.info("Validation passed, proceeding with capture")
                            self.status_label.config(text="Validation passed, proceeding with capture...")
                            self.root.update()
                            break
                        else:
                            print("[CAPTURE] Validation failed (hands detected in validation frames), retrying...")
                            logger.info("Validation failed (hands detected in validation frames), retrying...")
                            self.status_label.config(text="Validation failed, retrying...")
                            self.root.update()
                            retry_count += 1
                            time.sleep(1.0)
                            rgb_frame = self.oak.get_rgb()
                            if rgb_frame is None:
                                print("[CAPTURE] ERROR: Failed to recapture frame")
                                messagebox.showerror("Capture Error", "Failed to recapture frame from camera.")
                                self.status_label.config(text="Camera recapture failed.")
                                return
                            continue
                    
                    # Hand detected, wait and recapture
                    retry_count += 1
                    print(f"[CAPTURE] *** HAND DETECTED! Attempt {retry_count}, waiting 1 second and recapturing... ***")
                    logger.info(f"Hand detected in image (attempt {retry_count}), waiting 1 second and recapturing...")
                    self.status_label.config(text=f"Hand detected! Waiting 1 second and recapturing... (attempt {retry_count})")
                    self.root.update()
                    time.sleep(1.0)
                    
                    # Recapture
                    print(f"[CAPTURE] Recapturing frame...")
                    rgb_frame = self.oak.get_rgb()
                    if rgb_frame is None:
                        print("[CAPTURE] ERROR: Failed to recapture frame")
                        messagebox.showerror("Capture Error", "Failed to recapture frame from camera.")
                        self.status_label.config(text="Camera recapture failed.")
                        return
                    print(f"[CAPTURE] Frame recaptured, shape: {rgb_frame.shape}")
                
                if retry_count >= max_retries:
                    print(f"[CAPTURE] WARNING: Max retries ({max_retries}) reached, proceeding anyway")
                    logger.warning(f"Max retries ({max_retries}) reached, proceeding anyway")
                    self.status_label.config(text=f"Max retries reached, proceeding with capture...")
                    self.root.update()
            else:
                print("[CAPTURE] Hand detector is NOT available, skipping hand check")
            
            # Convert to RGB if needed (for display)
            if len(rgb_frame.shape) == 2:
                rgb_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_GRAY2RGB)
            
            # Save to temporary file
            temp_dir = Path(__file__).parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            # Clean up old temp file if exists
            if self.temp_image_path and os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                except:
                    pass
            
            # Save new capture
            self.temp_image_path = str(temp_dir / "camera_capture.jpg")
            cv2.imwrite(self.temp_image_path, cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR))
            
            # Load and display
            self.load_image(self.temp_image_path)
            self.status_label.config(text="Frame captured! Click on image to analyze.")
            logger.info(f"Captured frame from camera: {self.temp_image_path}")
            
        except Exception as e:
            error_msg = f"Error capturing from camera: {e}"
            logger.error(error_msg, exc_info=True)
            messagebox.showerror("Capture Error", error_msg)
            self.status_label.config(text=error_msg)
    
    def load_image(self, image_path: str):
        """Load and display an image at full size."""
        try:
            self.current_image_path = image_path
            # Load original image without resizing for display
            self.current_image = Image.open(image_path)
            
            # Create PhotoImage from full-size image
            # Note: Tkinter PhotoImage can handle large images, but may be slow for very large ones
            self.photo = ImageTk.PhotoImage(self.current_image)
            self.image_label.configure(image=self.photo, bg="gray")
            self.image_label.image = self.photo  # Keep a reference
            
            # Update canvas to properly show the full image
            self.canvas.update_idletasks()
            
            # Get the actual size of the image label after it's been configured
            label_width = self.image_label.winfo_reqwidth()
            label_height = self.image_label.winfo_reqheight()
            
            # Set scroll region to match the image size
            self.canvas.configure(scrollregion=(0, 0, label_width, label_height))
            
            # Ensure the canvas window is positioned correctly
            self.canvas.coords(self.image_window_id, 0, 0)
            
            self.status_label.config(
                text=f"Loaded: {Path(image_path).name} ({self.current_image.width}x{self.current_image.height})\nClick on image to analyze."
            )
            self.results_text.delete(1.0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
            self.status_label.config(text=f"Error loading image: {e}")
    
    def _on_image_click(self, event):
        """Handle click on image - trigger VLM analysis."""
        if not self.current_image_path:
            messagebox.showwarning("No Image", "Please load an image first.")
            return
        
        # Disable interaction during analysis
        self.status_label.config(text="Analyzing with Claude API...\nOptimizing image and sending request...")
        self.root.update()
        try:
            self.root.config(cursor="watch")  # "watch" is the standard cursor name
        except:
            self.root.config(cursor="")  # Fallback if cursor not supported
        
        try:
            logger.info("Starting VLM analysis")
            result = self.vlm_client.analyze_board(self.current_image_path, previous_result=self.last_result)
            self._display_results(result)
            self.status_label.config(text="Analysis complete!")
            logger.info("Analysis completed successfully")
            
        except ValueError as e:
            error_msg = f"Parsing error: {e}"
            logger.error(error_msg)
            self.status_label.config(text=error_msg)
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"ERROR:\n{error_msg}\n\nCheck debug/ folder for raw response.")
            messagebox.showerror("Analysis Error", f"{error_msg}\n\nCheck debug/ folder for details.")
        except Exception as e:
            error_msg = f"Error during analysis: {e}"
            logger.error(error_msg, exc_info=True)
            self.status_label.config(text=error_msg)
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"ERROR:\n{error_msg}\n\n")
            messagebox.showerror("Analysis Error", error_msg)
        finally:
            try:
                self.root.config(cursor="")
            except:
                pass  # Ignore cursor errors
    
    def _display_results(self, result: Dict):
        """Display analysis results in the text widget."""
        self.last_result = result
        self.export_btn.config(state=tk.NORMAL)
        if _REQUESTS_AVAILABLE:
            self.post_btn.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        
        output = []
        output.append("=" * 50)
        output.append("TILE EXTRACTION RESULTS")
        output.append("=" * 50)
        output.append("")
        
        # Display words by player
        player_words = result.get("player_words", {})
        if player_words:
            output.append("WORDS BY PLAYER:")
            output.append("-" * 50)
            
            total_words = 0
            for player, words in player_words.items():
                output.append(f"\n{player.upper()}:")
                if words:
                    for word_data in words:
                        word = word_data.get("word", "")
                        tiles = word_data.get("tiles", [])
                        tiles_str = " ".join(tiles) if tiles else "N/A"
                        output.append(f"  • {word} [{tiles_str}]")
                        total_words += 1
                else:
                    output.append("  (no words)")
                output.append("")
            output.append(f"Total words found: {total_words}")
            output.append("")
        else:
            output.append("No words found.")
            output.append("")
        
        # Display free letters
        free_letters = result.get("free_letters", [])
        output.append("FREE LETTERS (not in words):")
        output.append("-" * 50)
        if free_letters:
            output.append(f"  {', '.join(free_letters)}")
            output.append(f"\n  Total: {len(free_letters)} letters")
        else:
            output.append("  None")
        
        output.append("")
        output.append("=" * 50)
        
        # Write to text widget
        self.results_text.insert(tk.END, "\n".join(output))
    
    def _export_results(self):
        """Export results to JSON file."""
        if not self.last_result:
            messagebox.showwarning("No Results", "No results to export. Analyze an image first.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Results as JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.last_result, f, indent=2)
                messagebox.showinfo("Success", f"Results exported to:\n{file_path}")
                logger.info(f"Exported results to: {file_path}")
            except Exception as e:
                error_msg = f"Failed to export results: {e}"
                logger.error(error_msg)
                messagebox.showerror("Export Error", error_msg)
    
    def _transform_to_backend_format(self, result: Dict) -> Dict:
        """
        Transform VLM result format to backend format.
        
        Input format:
        {
            "player_words": {
                "player_1": [{"word": "HELLO", "tiles": ["H","E","L","L","O"]}, ...],
                "player_2": [{"word": "WORLD", "tiles": ["W","O","R","L","D"]}, ...]
            },
            "free_letters": ["A", "B", "C"]
        }
        
        Output format:
        {
            "players": [
                {"words": ["hello", "world"]},
                {"words": ["python"]}
            ],
            "availableLetters": "abc"
        }
        """
        backend_data = {
            "players": [],
            "availableLetters": ""
        }
        
        # Transform player_words to array format
        player_words = result.get("player_words", {})
        
        # Convert to list of player entries, preserving order
        # Handle both "player_1"/"player_2" and "left_player"/"right_player" formats
        player_keys = sorted(player_words.keys())
        
        for player_key in player_keys:
            words_list = player_words[player_key]
            # Extract just the word strings (lowercase) from word objects
            words = []
            for word_data in words_list:
                if isinstance(word_data, dict):
                    word = word_data.get("word", "")
                else:
                    word = str(word_data)
                if word:
                    words.append(word.lower())
            
            backend_data["players"].append({"words": words})
        
        # Transform free_letters array to concatenated string (lowercase)
        free_letters = result.get("free_letters", [])
        if free_letters:
            backend_data["availableLetters"] = "".join(letter.lower() for letter in free_letters)
        
        return backend_data
    
    def _post_to_backend(self):
        """Post results to backend API."""
        if not self.last_result:
            messagebox.showwarning("No Results", "No results to post. Analyze an image first.")
            return
        
        if not _REQUESTS_AVAILABLE:
            messagebox.showerror("Error", "requests package not installed.\nInstall with: pip install requests")
            return
        
        # Transform to backend format
        backend_data = self._transform_to_backend_format(self.last_result)
        
        self.status_label.config(text="Posting to backend...")
        self.root.update()
        
        try:
            # Post JSON to backend using dedicated session to avoid interference with image publisher
            if self.data_session is None:
                response = requests.post(
                    self.backend_url,
                    json=backend_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
            else:
                response = self.data_session.post(
                    self.backend_url,
                    json=backend_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
            
            # Check response
            response.raise_for_status()
            
            success_msg = f"Successfully posted to backend!\nStatus: {response.status_code}"
            if response.text:
                success_msg += f"\nResponse: {response.text[:100]}"
            
            self.status_label.config(text="Posted to backend successfully!")
            messagebox.showinfo("Success", success_msg)
            logger.info(f"Posted results to {self.backend_url}: {response.status_code}")
            logger.debug(f"Posted data: {json.dumps(backend_data, indent=2)}")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to post to backend: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nStatus: {e.response.status_code}"
                if e.response.text:
                    error_msg += f"\nResponse: {e.response.text[:200]}"
            
            logger.error(error_msg)
            self.status_label.config(text="Backend post failed.")
            messagebox.showerror("Post Error", error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg, exc_info=True)
            self.status_label.config(text="Backend post failed.")
            messagebox.showerror("Post Error", error_msg)
    
    def _toggle_auto_capture(self):
        """Start or stop automatic capture and analysis."""
        if not self.oak:
            messagebox.showerror("Camera Error", "Oak camera is not available.")
            return
        
        if self.auto_capture_running:
            # Stop auto-capture
            self.auto_capture_running = False
            if self.auto_capture_timer:
                self.auto_capture_timer.cancel()
                self.auto_capture_timer = None
            self.auto_capture_btn.config(text="Start Auto-Capture (15s)", bg="#4CAF50")
            self.status_label.config(text="Auto-capture stopped.")
            logger.info("Auto-capture stopped")
        else:
            # Start auto-capture
            self.auto_capture_running = True
            self.auto_capture_btn.config(text="Stop Auto-Capture", bg="#F44336")
            self.status_label.config(text="Auto-capture started. Capturing every 15 seconds...")
            logger.info("Auto-capture started")
            # Start the first cycle immediately
            self._schedule_next_capture()
    
    def _schedule_next_capture(self):
        """Schedule the next auto-capture cycle."""
        if not self.auto_capture_running:
            return
        
        # Run the capture cycle in a separate thread to avoid blocking GUI
        thread = threading.Thread(target=self._auto_capture_cycle, daemon=True)
        thread.start()
        
        # Schedule next capture in 15 seconds
        self.auto_capture_timer = threading.Timer(15.0, self._schedule_next_capture)
        self.auto_capture_timer.start()
    
    def _auto_capture_cycle(self):
        """Perform one complete cycle: capture -> analyze -> post."""
        if not self.auto_capture_running:
            return
        
        try:
            # Step 1: Capture from camera
            self.root.after(0, lambda: self.status_label.config(text="Auto-capturing from camera..."))
            logger.info("Auto-capture: Capturing frame from camera")
            
            if self.oak is None:
                logger.error("Auto-capture: Camera not available")
                return
            
            # Get RGB frame from camera (for hand detection)
            rgb_frame = self.oak.get_rgb()
            if rgb_frame is None:
                logger.warning("Auto-capture: Failed to capture frame")
                self.root.after(0, lambda: self.status_label.config(text="Auto-capture: Failed to capture frame"))
                return
            
            # Check for hands if detector is available - keep retrying until no hand is detected
            if self.hand_detector is not None:
                print("[AUTO-CAPTURE] Hand detector is available, checking for hands...")
                max_retries = 100  # Safety limit to prevent infinite loop
                retry_count = 0
                
                while retry_count < max_retries:
                    print(f"[AUTO-CAPTURE] Checking for hands (attempt {retry_count + 1})...")
                    has_hands = self.hand_detector.detect_hands(rgb_frame)
                    print(f"[AUTO-CAPTURE] Hand detection result: {has_hands}")
                    
                    if not has_hands:
                        print("[AUTO-CAPTURE] No hand detected, validating with multiple frames...")
                        logger.info("Auto-capture: No hand detected, validating with multiple frames...")
                        self.root.after(0, lambda: self.status_label.config(text="Auto-capture: No hand detected, validating with multiple frames..."))
                        
                        # Validate with multiple frames
                        validated_frame, all_clear = self._validate_no_hands_multiple_frames(rgb_frame)
                        rgb_frame = validated_frame
                        
                        if all_clear:
                            print("[AUTO-CAPTURE] Validation passed, proceeding with capture")
                            logger.info("Auto-capture: Validation passed, proceeding with capture")
                            self.root.after(0, lambda: self.status_label.config(text="Auto-capture: Validation passed, proceeding..."))
                            break
                        else:
                            print("[AUTO-CAPTURE] Validation failed (hands detected in validation frames), retrying...")
                            logger.info("Auto-capture: Validation failed (hands detected in validation frames), retrying...")
                            self.root.after(0, lambda: self.status_label.config(text="Auto-capture: Validation failed, retrying..."))
                            retry_count += 1
                            time.sleep(1.0)
                            rgb_frame = self.oak.get_rgb()
                            if rgb_frame is None:
                                print("[AUTO-CAPTURE] ERROR: Failed to recapture frame")
                                logger.warning("Auto-capture: Failed to recapture frame")
                                self.root.after(0, lambda: self.status_label.config(text="Auto-capture: Failed to recapture frame"))
                                return
                            continue
                    
                    # Hand detected, wait and recapture
                    retry_count += 1
                    print(f"[AUTO-CAPTURE] *** HAND DETECTED! Attempt {retry_count}, waiting 1 second and recapturing... ***")
                    logger.info(f"Auto-capture: Hand detected in image (attempt {retry_count}), waiting 1 second and recapturing...")
                    self.root.after(0, lambda c=retry_count: self.status_label.config(text=f"Auto-capture: Hand detected! Waiting 1 second and recapturing... (attempt {c})"))
                    time.sleep(1.0)
                    
                    # Recapture
                    print(f"[AUTO-CAPTURE] Recapturing frame...")
                    rgb_frame = self.oak.get_rgb()
                    if rgb_frame is None:
                        print("[AUTO-CAPTURE] ERROR: Failed to recapture frame")
                        logger.warning("Auto-capture: Failed to recapture frame")
                        self.root.after(0, lambda: self.status_label.config(text="Auto-capture: Failed to recapture frame"))
                        return
                    print(f"[AUTO-CAPTURE] Frame recaptured, shape: {rgb_frame.shape}")
                
                if retry_count >= max_retries:
                    print(f"[AUTO-CAPTURE] WARNING: Max retries ({max_retries}) reached, proceeding anyway")
                    logger.warning(f"Auto-capture: Max retries ({max_retries}) reached, proceeding anyway")
                    self.root.after(0, lambda: self.status_label.config(text=f"Auto-capture: Max retries reached, proceeding..."))
            else:
                print("[AUTO-CAPTURE] Hand detector is NOT available, skipping hand check")
            
            # Convert to RGB if needed (for display)
            if len(rgb_frame.shape) == 2:
                rgb_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_GRAY2RGB)
            
            # Save to temporary file
            temp_dir = Path(__file__).parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            # Clean up old temp file if exists
            if self.temp_image_path and os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                except:
                    pass
            
            # Save new capture
            self.temp_image_path = str(temp_dir / "camera_capture.jpg")
            cv2.imwrite(self.temp_image_path, cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR))
            
            # Update GUI with captured image
            self.root.after(0, lambda: self.load_image(self.temp_image_path))
            logger.info(f"Auto-capture: Frame saved to {self.temp_image_path}")
            
            # Step 2: Analyze with Claude
            self.root.after(0, lambda: self.status_label.config(text="Auto-capture: Analyzing with Claude..."))
            logger.info("Auto-capture: Starting VLM analysis")
            
            # Get previous result for context (thread-safe access)
            previous_result = self.last_result
            result = self.vlm_client.analyze_board(self.temp_image_path, previous_result=previous_result)
            
            # Update GUI with results
            self.root.after(0, lambda: self._display_results(result))
            logger.info("Auto-capture: Analysis completed")
            
            # Step 3: Post to backend
            if result and _REQUESTS_AVAILABLE:
                self.root.after(0, lambda: self.status_label.config(text="Auto-capture: Posting to backend..."))
                logger.info("Auto-capture: Posting to backend")
                
                backend_data = self._transform_to_backend_format(result)
                
                try:
                    # Use dedicated session for update-data requests
                    if self.data_session is None:
                        response = requests.post(
                            self.backend_url,
                            json=backend_data,
                            headers={"Content-Type": "application/json"},
                            timeout=10.0
                        )
                    else:
                        response = self.data_session.post(
                            self.backend_url,
                            json=backend_data,
                            headers={"Content-Type": "application/json"},
                            timeout=10.0
                        )
                    response.raise_for_status()
                    logger.info(f"Auto-capture: Posted to backend successfully (Status: {response.status_code})")
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"Auto-capture complete! Posted to backend. Next capture in 15s..."
                    ))
                except Exception as e:
                    logger.error(f"Auto-capture: Failed to post to backend: {e}")
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"Auto-capture: Analysis complete but post failed. Next capture in 15s..."
                    ))
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Auto-capture complete! Next capture in 15s..."
                ))
            
        except Exception as e:
            logger.error(f"Auto-capture cycle error: {e}", exc_info=True)
            self.root.after(0, lambda: self.status_label.config(
                text=f"Auto-capture error: {e}. Retrying in 15s..."
            ))
    
    def _toggle_publisher(self):
        """Start or stop the tile publisher loop."""
        if not self.oak:
            messagebox.showerror("Camera Error", "Oak camera is not available.")
            return
        
        if not self.tile_publisher:
            messagebox.showerror("Publisher Error", "TilePublisher is not available.")
            return
        
        if self.publisher_running:
            # Stop publisher
            self.publisher_running = False
            if self.publisher_thread and self.publisher_thread.is_alive():
                # Wait a bit for thread to finish
                self.publisher_thread.join(timeout=2.0)
            self.publisher_btn.config(text="Start Tile Publisher (3s)", bg="#FF5722")
            self.status_label.config(text="Tile publisher stopped.")
            logger.info("Tile publisher stopped")
        else:
            # Start publisher
            self.publisher_running = True
            self.publisher_btn.config(text="Stop Tile Publisher", bg="#F44336")
            self.status_label.config(text="Tile publisher started. Publishing every 3 seconds...")
            logger.info("Tile publisher started")
            # Start the publisher loop in a separate thread
            self.publisher_thread = threading.Thread(target=self._publisher_loop, daemon=True)
            self.publisher_thread.start()
    
    def _publisher_loop(self):
        """Publisher loop: capture frame and publish to backend."""
        interval = 3.0  # seconds between captures
        
        while self.publisher_running:
            try:
                # Get RGB frame from camera (same source as other captures)
                if self.oak is None:
                    logger.error("Publisher: Camera not available")
                    break
                
                rgb_frame = self.oak.get_rgb()
                if rgb_frame is None:
                    logger.warning("Publisher: Failed to capture frame")
                    time.sleep(interval)
                    continue
                
                # Convert RGB to BGR for publisher (publisher expects BGR)
                bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
                
                # Publish to backend
                self.tile_publisher.publish(bgr_frame)
                
                logger.info("Publisher: Frame published to backend")
                
                # Wait for next cycle
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Publisher loop error: {e}", exc_info=True)
                time.sleep(interval)
        
        logger.info("Publisher loop stopped")
    
    def run(self):
        """Start the GUI event loop."""
        # Set up window close handler
        def on_closing():
            # Stop auto-capture if running
            if self.auto_capture_running:
                self.auto_capture_running = False
                if self.auto_capture_timer:
                    self.auto_capture_timer.cancel()
            # Stop publisher if running
            if self.publisher_running:
                self.publisher_running = False
                if self.publisher_thread and self.publisher_thread.is_alive():
                    self.publisher_thread.join(timeout=2.0)
            # Cleanup
            if self.temp_image_path and os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                except:
                    pass
            if self.oak is not None:
                try:
                    self.oak.close()
                except:
                    pass
            # Cleanup data session
            if self.data_session is not None:
                try:
                    self.data_session.close()
                except:
                    pass
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        try:
            self.root.mainloop()
        finally:
            # Cleanup
            if self.auto_capture_running:
                self.auto_capture_running = False
                if self.auto_capture_timer:
                    self.auto_capture_timer.cancel()
            if self.publisher_running:
                self.publisher_running = False
                if self.publisher_thread and self.publisher_thread.is_alive():
                    self.publisher_thread.join(timeout=2.0)
            if self.temp_image_path and os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                except:
                    pass
            if self.oak is not None:
                try:
                    self.oak.close()
                except:
                    pass
            # Cleanup data session
            if self.data_session is not None:
                try:
                    self.data_session.close()
                except:
                    pass


def load_api_key() -> str:
    """Load Claude API key from secret.txt."""
    secret_path = Path(__file__).parent / "secret.txt"
    if not secret_path.exists():
        raise FileNotFoundError(
            f"API key file not found: {secret_path}\n"
            "Please create secret.txt with your Claude API key."
        )
    
    with open(secret_path, 'r') as f:
        api_key = f.read().strip()
    
    if not api_key:
        raise ValueError("API key file is empty.")
    
    return api_key


def main():
    """Main entry point."""
    try:
        api_key = load_api_key()
        app = TileExtractorGUI(api_key)
        app.run()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

