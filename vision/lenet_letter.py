"""LeNet-style CNN for single-letter classification (A–Z). Input: 32×32 grayscale."""

import os
import numpy as np
import torch
import torch.nn as nn

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
NUM_CLASSES = 26
INPUT_SIZE = 32
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "models", "lenet_letter.pt"
)
MIN_CONFIDENCE = 50.0  # below this, return None (unknown)


def _flatten_size(h, w):
    """After Conv(3) no padding: -2 each. After MaxPool(2): //2 each."""
    for _ in range(2):
        h, w = h - 2, w - 2
        h, w = h // 2, w // 2
    return 32 * h * w


class LeNetLetter(nn.Module):
    """
    LeNet-style: Conv(1,16,3) ReLU MaxPool(2) -> Conv(16,32,3) ReLU MaxPool(2) -> Flatten -> Linear(?, 128) ReLU -> Linear(128, 26).
    Flatten size computed from input resolution (default 32×32).
    """

    def __init__(self, num_classes=NUM_CLASSES, input_size=INPUT_SIZE):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3)
        self.pool = nn.MaxPool2d(2)
        self.relu = nn.ReLU()
        flat = _flatten_size(input_size, input_size)
        self.fc1 = nn.Linear(flat, 128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x


class LeNetLetterRecognizer:
    """Load trained LeNetLetter and run inference on tile crops. Same interface as LetterCNNRecognizer."""

    def __init__(self, model_path=None, device=None):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self._load()

    def _load(self):
        if not os.path.isfile(self.model_path):
            raise FileNotFoundError(f"No model at {self.model_path}. Run train_lenet_letter.py first.")
        self.model = LeNetLetter(num_classes=NUM_CLASSES, input_size=INPUT_SIZE)
        state = torch.load(self.model_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.to(self.device).eval()
        print(f"LeNetLetter loaded from {self.model_path} ({self.device})")

    @staticmethod
    def _crop_to_tensor(crop, size=INPUT_SIZE):
        """Crop -> tensor. Match train_lenet_letter: grayscale, resize, [0,1]."""
        if crop.ndim > 2:
            crop = np.mean(crop, axis=2)
        crop = np.asarray(crop, dtype=np.float32) / 255.0
        import cv2
        crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_LINEAR)
        t = torch.from_numpy(crop.astype(np.float32)).unsqueeze(0).unsqueeze(0)
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
