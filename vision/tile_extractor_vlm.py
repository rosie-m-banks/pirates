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


class VLMClient:
    """Client for interacting with Claude API."""
    
    def __init__(self, api_key: str):
        """Initialize Anthropic client with API key."""
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-20241022"  # Fast and cost-effective
    
    def analyze_board(self, image_path: str, max_size: int = 1024, quality: int = 85) -> Dict:
        """
        Send image to VLM and get structured analysis.
        
        Args:
            image_path: Path to image file
            max_size: Maximum dimension (width or height) for resizing (default: 1024)
            quality: JPEG quality for compression (1-100, default: 85)
        
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
        
        prompt = """Analyze this Bananagrams board image. Extract all tiles organized by words and players.

Instructions:
1. Identify all words (tiles connected horizontally or vertically)
2. Group words by player based on orientation/side:
   - Words oriented one way belong to one player
   - Words oriented differently belong to another player
3. List free letters (not connected to any word)

Return JSON only:
{
    "player_words": {
        "player_1": [{"word": "HELLO", "tiles": ["H","E","L","L","O"]}],
        "player_2": [{"word": "WORLD", "tiles": ["W","O","R","L","D"]}]
    },
    "free_letters": ["A","B","C"]
}

Be concise. Each tile = single uppercase letter (A-Z). Only include clearly visible tiles."""

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
        self.backend_url: str = "http://localhost:3000/update-api"
        
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
    
    def _capture_from_camera(self):
        """Capture a frame from the Oak camera."""
        if self.oak is None:
            messagebox.showerror("Camera Error", "Oak camera is not available.")
            return
        
        self.status_label.config(text="Capturing frame from camera...")
        self.root.update()
        
        try:
            # Get grayscale frame from camera
            gray_frame = self.oak.get_gray()
            
            if gray_frame is None:
                messagebox.showerror("Capture Error", "Failed to capture frame from camera.\nCamera may not be ready yet.")
                self.status_label.config(text="Camera capture failed.")
                return
            
            # Convert grayscale to RGB for display (VLM can handle grayscale but RGB is better)
            # We'll convert to 3-channel for consistency
            if len(gray_frame.shape) == 2:
                rgb_frame = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2RGB)
            else:
                rgb_frame = gray_frame
            
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
            result = self.vlm_client.analyze_board(self.current_image_path)
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
            # Post JSON to backend
            response = requests.post(
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
    
    def run(self):
        """Start the GUI event loop."""
        try:
            self.root.mainloop()
        finally:
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

