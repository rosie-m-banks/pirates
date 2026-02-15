"""Small CNN for Bananagram letter recognition (A–Z). Fast inference, robust to variations."""

import os
import numpy as np
import torch
import torch.nn as nn

INPUT_SIZE = 64
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
NUM_CLASSES = len(LETTERS)
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "models", "letter_cnn.pt"
)


class LetterCNN(nn.Module):
    """Lightweight CNN: 64x64 grayscale -> 26 classes. ~100k params."""

    def __init__(self, num_classes=NUM_CLASSES):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.25),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)


MIN_CONFIDENCE = 50.0  # below this, return None (unknown)


class LetterCNNRecognizer:
    """Load trained LetterCNN and run inference on tile crops."""

    def __init__(self, model_path=None, device=None):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self._load()

    def _load(self):
        if not os.path.isfile(self.model_path):
            raise FileNotFoundError(f"No model at {self.model_path}. Run train_letter_model.py first.")
        self.model = LetterCNN(num_classes=NUM_CLASSES)
        state = torch.load(self.model_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.to(self.device).eval()
        print(f"LetterCNN loaded from {self.model_path} ({self.device})")

    @staticmethod
    def _crop_to_tensor(crop, size=INPUT_SIZE):
        """Crop (H,W) or (H,W,3) -> tensor (1, 1, size, size) in [0,1]."""
        if crop.ndim > 2:
            crop = np.mean(crop, axis=2)
        crop = np.asarray(crop, dtype=np.float32) / 255.0
        import cv2
        crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_LINEAR)
        t = torch.from_numpy(crop).unsqueeze(0).unsqueeze(0)
        return t

    def predict_batch(self, crops):
        """crops: list of (H,W) or (H,W,3) numpy. Returns list of (letter_or_None, confidence_0_100)."""
        if not crops:
            return []
        tensors = [self._crop_to_tensor(c) for c in crops]
        x = torch.cat(tensors, dim=0).to(self.device)
        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1)
        results = []
        for i in range(len(crops)):
            p = probs[i]
            conf, idx = p.max(dim=0)
            idx = idx.item()
            conf = conf.item()
            conf_pct = min(100.0, conf * 100.0)
            if conf_pct < MIN_CONFIDENCE:
                results.append((None, 0.0))
            else:
                results.append((LETTERS[idx], conf_pct))
        return results

    @property
    def available(self):
        return self.model is not None
