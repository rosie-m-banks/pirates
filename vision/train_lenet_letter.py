"""
Train and evaluate LeNet-style letter classifier (A–Z).
Data: letter_data/A, B, ..., Z. Preprocessing: grayscale, [0,1], 32×32, optional adaptive thresh.
Augmentation: ±5° rotation, small translation, mild brightness/contrast. Eval: per-class acc, confusion matrix.
"""

import os
import sys
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split, Subset
from torchvision import transforms, datasets
import cv2
from PIL import Image

from lenet_letter import LeNetLetter, LETTERS, NUM_CLASSES, INPUT_SIZE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(SCRIPT_DIR, "letter_data")
DEFAULT_MODEL_PATH = os.path.join(SCRIPT_DIR, "models", "lenet_letter.pt")
IMAGE_SIZE = 32
BATCH_SIZE = 32
EPOCHS = 500
LR = 1e-3
VAL_FRAC = 0.2
EARLY_STOP_PATIENCE = 70  # stop if no val improvement for this many epochs


# --------------- Preprocessing: optional adaptive threshold ---------------
def adaptive_thresh_pil(pil_img):
    """Apply adaptive threshold to PIL image; return PIL (grayscale)."""
    arr = np.array(pil_img)
    if arr.ndim == 3:
        arr = np.mean(arr, axis=2).astype(np.uint8)
    block = min(31, (min(arr.shape) // 4) | 1)
    arr = cv2.adaptiveThreshold(
        arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block, 8
    )
    return Image.fromarray(arr)


class ToTensorNormalize:
    """Convert PIL to tensor and normalize to [0, 1]."""

    def __call__(self, pil):
        arr = np.array(pil, dtype=np.float32)
        if arr.ndim == 3:
            arr = np.mean(arr, axis=2)
        arr = arr / 255.0
        return torch.from_numpy(arr).unsqueeze(0)


# --------------- Dataset: center crop, resize 32×32 ---------------
def get_train_transform(use_adaptive_thresh=False, image_size=IMAGE_SIZE):
    t = [
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((image_size, image_size)),
        transforms.CenterCrop(image_size),
    ]
    if use_adaptive_thresh:
        t.insert(1, transforms.Lambda(lambda x: adaptive_thresh_pil(x)))
    t.extend([
        transforms.RandomRotation(5, fill=255),
        transforms.RandomAffine(degrees=0, translate=(0.05, 0.05), fill=255),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        ToTensorNormalize(),
    ])
    return transforms.Compose(t)


def get_val_transform(use_adaptive_thresh=False, image_size=IMAGE_SIZE):
    t = [
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((image_size, image_size)),
        transforms.CenterCrop(image_size),
        ToTensorNormalize(),
    ]
    if use_adaptive_thresh:
        t.insert(1, transforms.Lambda(lambda x: adaptive_thresh_pil(x)))
    return transforms.Compose(t)


# --------------- Sanity checks ---------------
def sanity_checks(data_dir, train_sub, val_subset, class_to_idx):
    print("\n--- Sanity checks ---")
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    counts = {}
    for i in range(len(train_sub)):
        _, y = train_sub[i]
        key = idx_to_class[y.item() if torch.is_tensor(y) else y]
        counts[key] = counts.get(key, 0) + 1
    for i in range(len(val_subset)):
        _, y = val_subset[i]
        key = idx_to_class[y.item() if torch.is_tensor(y) else y]
        counts[key] = counts.get(key, 0) + 1
    print("Class counts:", dict(sorted(counts.items())))
    if len(counts) < 26:
        print("WARNING: Not all 26 classes present in dataset.")
    for c, cnt in counts.items():
        if cnt == 0:
            print("WARNING: Empty class", c)
    print("Label mapping (first 5):", {i: idx_to_class[i] for i in range(min(5, len(idx_to_class)))})
    # Visualize one batch
    loader = DataLoader(train_sub, batch_size=min(8, len(train_sub)), shuffle=True)
    x, y = next(iter(loader))
    print("Batch tensor shape:", x.shape, "dtype:", x.dtype, "min/max:", x.min().item(), x.max().item())
    print("Batch labels (first 8):", [idx_to_class.get(y[i].item(), "?") for i in range(min(8, len(y)))])
    print("--- End sanity checks ---\n")


# --------------- Training ---------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DEFAULT_DATA_DIR)
    ap.add_argument("--out", default=DEFAULT_MODEL_PATH)
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--lr", type=float, default=LR)
    ap.add_argument("--batch", type=int, default=BATCH_SIZE)
    ap.add_argument("--patience", type=int, default=EARLY_STOP_PATIENCE, help="Early stop if no val improvement for this many epochs")
    ap.add_argument("--no-adaptive", action="store_true", help="Disable adaptive thresholding (default: on for consistent contrast)")
    args = ap.parse_args()
    use_adaptive = not args.no_adaptive

    if not os.path.isdir(args.data):
        print("Data dir not found:", args.data)
        return 1
    if use_adaptive:
        print("Using adaptive thresholding for consistent contrast.")
    for letter in LETTERS:
        os.makedirs(os.path.join(args.data, letter), exist_ok=True)

    train_tf = get_train_transform(use_adaptive_thresh=use_adaptive)
    val_tf = get_val_transform(use_adaptive_thresh=use_adaptive)
    full_ds = datasets.ImageFolder(args.data, transform=train_tf)
    val_ds = datasets.ImageFolder(args.data, transform=val_tf)
    n = len(full_ds)
    if n == 0:
        print("No images in letter_data. Add images to A/, B/, ..., Z/.")
        return 1

    val_frac = VAL_FRAC if n >= 80 else 0.1
    n_val = max(1, min(int(n * val_frac), n - 1))
    n_train = n - n_val
    if n < 80:
        print(f"Small dataset ({n} samples): using 10% for validation to maximize training data.")
    train_sub, val_sub = random_split(full_ds, [n_train, n_val], generator=torch.Generator().manual_seed(42))
    val_subset = Subset(val_ds, val_sub.indices)
    train_loader = DataLoader(train_sub, batch_size=args.batch, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_subset, batch_size=args.batch, shuffle=False, num_workers=0)

    sanity_checks(args.data, train_sub, val_subset, full_ds.class_to_idx)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LeNetLetter(num_classes=NUM_CLASSES, input_size=IMAGE_SIZE).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    idx_to_class = {v: k for k, v in full_ds.class_to_idx.items()}
    best_val_acc = 0.0
    epochs_no_improve = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_correct, train_total = 0, 0
        train_loss_sum = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            opt.step()
            train_loss_sum += loss.item()
            pred = logits.argmax(dim=1)
            train_correct += (pred == y).sum().item()
            train_total += y.size(0)
        train_acc = train_correct / train_total
        train_loss = train_loss_sum / len(train_loader)

        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                logits = model(x)
                pred = logits.argmax(dim=1)
                val_correct += (pred == y).sum().item()
                val_total += y.size(0)
        val_acc = val_correct / val_total if val_total else 0.0
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            epochs_no_improve = 0
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            torch.save(model.state_dict(), args.out)
            print(f"Epoch {epoch}/{args.epochs}  loss={train_loss:.4f}  train_acc={train_acc:.2%}  val_acc={val_acc:.2%}  [saved]")
        else:
            epochs_no_improve += 1
            print(f"Epoch {epoch}/{args.epochs}  loss={train_loss:.4f}  train_acc={train_acc:.2%}  val_acc={val_acc:.2%}")
        if epochs_no_improve >= args.patience:
            print(f"Early stopping (no improvement for {args.patience} epochs).")
            break

    # --------------- Evaluation: per-class accuracy, confusion matrix ---------------
    print("\n--- Evaluation ---")
    if os.path.isfile(args.out):
        model.load_state_dict(torch.load(args.out, map_location=device, weights_only=True))
    model.eval()
    all_pred, all_true = [], []
    with torch.no_grad():
        for x, y in val_loader:
            x = x.to(device)
            logits = model(x)
            pred = logits.argmax(dim=1)
            all_pred.extend(pred.cpu().numpy().tolist())
            all_true.extend(y.numpy().tolist())
    all_pred = np.array(all_pred)
    all_true = np.array(all_true)

    # Per-class accuracy
    print("Per-class accuracy (val set):")
    for c in range(NUM_CLASSES):
        mask = all_true == c
        if mask.sum() == 0:
            print(f"  {idx_to_class[c]}: no samples")
            continue
        acc = (all_pred[mask] == c).mean()
        print(f"  {idx_to_class[c]}: {acc:.2%} (n={mask.sum()})")
    overall = (all_pred == all_true).mean()
    print(f"Overall val accuracy: {overall:.2%}")

    # Confusion matrix (26x26)
    cm = np.zeros((NUM_CLASSES, NUM_CLASSES), dtype=np.int64)
    for t, p in zip(all_true, all_pred):
        cm[t, p] += 1
    print("\nConfusion matrix (rows=true, cols=pred):")
    print("   " + " ".join(idx_to_class[i] for i in range(NUM_CLASSES)))
    for i in range(NUM_CLASSES):
        row = " ".join(f"{cm[i, j]:3d}" for j in range(NUM_CLASSES))
        print(f"{idx_to_class[i]}  {row}")

    # Manually inspect a few
    print("\nSample predictions (first 10 val):")
    for i in range(min(10, len(all_true))):
        t = all_true[i]
        p = all_pred[i]
        ok = "OK" if t == p else "WRONG"
        print(f"  true={idx_to_class[t]}  pred={idx_to_class[p]}  {ok}")

    print(f"\nModel saved to {args.out}")
    if overall < 0.95:
        if n < 100:
            print("Accuracy below 95%: add more images per letter (5-10+ per class) for higher accuracy.")
        else:
            print("Accuracy below 95%: check preprocessing, augmentation severity, and label mapping.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
