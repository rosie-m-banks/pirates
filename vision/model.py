import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import os
import string
import random

# ── Dataset ─────────────────────────────────────
class TileDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.samples = []
        self.transform = transform
        for letter in string.ascii_uppercase:
            path = os.path.join(root_dir, letter + ".png")
            if os.path.exists(path):
                self.samples.append((path, ord(letter)-65))  # A=0, B=1...
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("L")  # grayscale
        if self.transform:
            img = self.transform(img)
        return img, label

# ── Augmentations ──────────────────────────────
transform = transforms.Compose([
    transforms.RandomRotation(90),  # rotate 0-90 degrees
    transforms.RandomAffine(degrees=0, translate=(0.1,0.1), scale=(0.8,1.2)),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.Resize((64,64)),
    transforms.ToTensor(),
])

dataset = TileDataset("crops-01/", transform=transform)
loader = DataLoader(dataset, batch_size=4, shuffle=True)

# ── CNN ───────────────────────────────────────
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2)
        )
        self.fc = nn.Sequential(
            nn.Linear(128*8*8, 256), nn.ReLU(),
            nn.Linear(256, 26)
        )
    
    def forward(self, x):
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SimpleCNN().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=1e-3)

# ── Training ─────────────────────────────────
epochs = 50
for epoch in range(epochs):
    model.train()
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        output = model(imgs)
        loss = criterion(output, labels)
        loss.backward()
        optimizer.step()
    print(f"Epoch {epoch+1}/{epochs} done, loss={loss.item():.4f}")

# ── Save model ───────────────────────────────
torch.save(model.state_dict(), "tile_cnn.pth")
