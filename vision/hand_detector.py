#!/usr/bin/env python3
"""
Hand detection utility using MediaPipe Hands.
Detects if there are any hands in an image.
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    _MEDIAPIPE_AVAILABLE = True
    print(f"[HAND_DETECTOR] MediaPipe imported successfully! Version: {mp.__version__}")
except ImportError as e:
    mp = None
    python = None
    vision = None
    _MEDIAPIPE_AVAILABLE = False
    print(f"[HAND_DETECTOR] MediaPipe import failed: {e}")
    print(f"[HAND_DETECTOR] ImportError type: {type(e).__name__}")
    logger.warning("MediaPipe not available. Install with: pip install mediapipe")
except Exception as e:
    mp = None
    python = None
    vision = None
    _MEDIAPIPE_AVAILABLE = False
    print(f"[HAND_DETECTOR] MediaPipe import error (not ImportError): {e}")
    print(f"[HAND_DETECTOR] Error type: {type(e).__name__}")
    logger.warning(f"MediaPipe not available due to error: {e}")


class HandDetector:
    """Detects hands in images using MediaPipe Hands."""
    
    def __init__(self):
        """Initialize MediaPipe Hands detector."""
        if not _MEDIAPIPE_AVAILABLE:
            raise ImportError("MediaPipe not available. Install with: pip install mediapipe")
        
        try:
            # Use the new MediaPipe 0.10+ API
            import os
            from pathlib import Path
            model_path = Path(__file__).parent / "models" / "hand_landmarker.task"
            
            if not model_path.exists():
                raise FileNotFoundError(f"Hand landmarker model not found at {model_path}")
            
            print(f"[HAND_DETECTOR] Using model file: {model_path}")
            base_options = python.BaseOptions(model_asset_path=str(model_path))
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
            self.use_legacy_api = False
            print("[HAND_DETECTOR] HandLandmarker initialized successfully")
            logger.info("HandDetector initialized")
        except Exception as e:
            print(f"[HAND_DETECTOR] Failed to initialize HandLandmarker: {e}")
            # Try fallback to legacy API if available
            try:
                if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'hands'):
                    print("[HAND_DETECTOR] Falling back to legacy solutions.hands API")
                    self.mp_hands = mp.solutions.hands
                    self.hands = self.mp_hands.Hands(
                        static_image_mode=True,
                        max_num_hands=2,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    self.use_legacy_api = True
                    logger.info("HandDetector initialized with legacy API")
                else:
                    raise e
            except Exception as e2:
                raise ImportError(f"Failed to initialize MediaPipe hand detector: {e2}")
    
    def detect_hands(self, image: np.ndarray) -> bool:
        """
        Detect if there are any hands in the image.
        
        Args:
            image: BGR or RGB numpy array (OpenCV format)
        
        Returns:
            True if at least one hand is detected, False otherwise
        """
        print(f"[HAND DETECTOR] detect_hands() called - MediaPipe available: {_MEDIAPIPE_AVAILABLE}")
        
        if not _MEDIAPIPE_AVAILABLE:
            print("[HAND DETECTOR] MediaPipe not available, skipping hand detection")
            logger.warning("MediaPipe not available, skipping hand detection")
            return False
        
        try:
            # MediaPipe expects RGB images
            if len(image.shape) == 2:
                # Grayscale image, convert to RGB
                print("[HAND DETECTOR] Converting grayscale to RGB")
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 3:
                # Check if it's BGR (OpenCV default) or RGB
                # MediaPipe expects RGB, so convert BGR to RGB
                print("[HAND DETECTOR] Converting BGR to RGB")
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                # Already RGB or other format
                print(f"[HAND DETECTOR] Image shape: {image.shape}, assuming RGB")
                rgb_image = image
            
            print(f"[HAND DETECTOR] Running MediaPipe hand detection on image shape: {rgb_image.shape}")
            
            # Check if we're using legacy API
            if hasattr(self, 'use_legacy_api') and self.use_legacy_api:
                # Legacy API
                results = self.hands.process(rgb_image)
                has_hands = results.multi_hand_landmarks is not None and len(results.multi_hand_landmarks) > 0
            else:
                # New API (0.10+)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
                detection_result = self.hand_landmarker.detect(mp_image)
                has_hands = detection_result.hand_landmarks is not None and len(detection_result.hand_landmarks) > 0
            
            if has_hands:
                if hasattr(self, 'use_legacy_api') and self.use_legacy_api:
                    num_hands = len(results.multi_hand_landmarks)
                else:
                    num_hands = len(detection_result.hand_landmarks)
                print(f"[HAND DETECTOR] *** HAND DETECTED! Found {num_hands} hand(s) in image ***")
                logger.info(f"Detected {num_hands} hand(s) in image")
            else:
                print("[HAND DETECTOR] No hands detected in image")
                logger.debug("No hands detected in image")
            
            return has_hands
            
        except Exception as e:
            print(f"[HAND DETECTOR] ERROR during hand detection: {e}")
            logger.error(f"Error during hand detection: {e}", exc_info=True)
            # On error, assume no hands (fail open) to avoid blocking captures
            return False
    
    def __del__(self):
        """Cleanup MediaPipe resources."""
        if hasattr(self, 'hand_landmarker') and self.hand_landmarker is not None:
            try:
                self.hand_landmarker.close()
            except:
                pass
        if hasattr(self, 'hands') and self.hands is not None:
            try:
                self.hands.close()
            except:
                pass
