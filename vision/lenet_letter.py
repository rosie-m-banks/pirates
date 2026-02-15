"""LeNet-style CNN for single-letter classification (A–Z). Input: 32×32 grayscale."""

import torch
import torch.nn as nn

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
NUM_CLASSES = 26
INPUT_SIZE = 32


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
