"""Pretrained single-character recogniser using TrOCR (microsoft/trocr-small-printed)."""

import torch
import numpy as np
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

MODEL_NAME = "microsoft/trocr-small-printed"


class LetterRecognizer:
    """Thin wrapper around TrOCR for single-letter classification on GPU."""

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.processor, self.model = self._load()
        self.model.to(self.device).eval()
        print(f"LetterRecognizer ready on {self.device}")

    def _load(self):
        """Load from HuggingFace (uses their cache; no local save to avoid path bugs)."""
        print(f"Loading TrOCR from {MODEL_NAME}...")
        # use_fast=False avoids a transformers bug where vocab_file is None (AttributeError: endswith)
        processor = TrOCRProcessor.from_pretrained(MODEL_NAME, use_fast=False)
        model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
        return processor, model

    # ── Public API ───────────────────────────────────────────────────

    def predict_batch(self, images):
        """Classify a batch of grayscale numpy arrays.

        Args:
            images: list of 2-D uint8 numpy arrays (grayscale tile crops)

        Returns:
            list of (letter_or_None, confidence) tuples
        """
        if not images:
            return []

        pil_imgs = [self._to_pil(img) for img in images]
        pixel_values = self.processor(
            pil_imgs, return_tensors="pt"
        ).pixel_values.to(self.device)

        with torch.no_grad():
            gen = self.model.generate(
                pixel_values,
                max_new_tokens=3,
                output_scores=True,
                return_dict_in_generate=True,
            )

        results = []
        for i in range(len(images)):
            text = self.processor.decode(gen.sequences[i], skip_special_tokens=True).strip()
            letter = self._first_alpha(text)

            # Confidence from first generated token's softmax
            if gen.scores:
                probs = torch.softmax(gen.scores[0][i], dim=-1)
                token_id = gen.sequences[i, 1]  # skip BOS
                conf = probs[token_id].item()
            else:
                conf = 0.0

            results.append((letter, conf))

        return results

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _to_pil(gray):
        """Convert a grayscale numpy array to an RGB PIL Image."""
        if len(gray.shape) == 2:
            rgb = np.stack([gray, gray, gray], axis=-1)
        else:
            rgb = gray
        return Image.fromarray(rgb)

    @staticmethod
    def _first_alpha(text):
        """Return the first uppercase letter in text, or None."""
        for ch in text.upper():
            if ch.isalpha():
                return ch
        return None
