"""Train the LetterCNN on labeled tile crops. Run once you have data in letter_data/."""

import os
import argparse
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split, Subset
from torchvision import transforms, datasets

from letter_cnn import LetterCNN, NUM_CLASSES, LETTERS, DEFAULT_MODEL_PATH

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(SCRIPT_DIR, "letter_data")
INPUT_SIZE = 64
BATCH_SIZE = 32
EPOCHS = 200
LR = 1e-3
VAL_FRAC = 0.15
EARLY_STOP_PATIENCE = 35  # stop if no val improvement for this many epochs


def main():
    ap = argparse.ArgumentParser(description="Train LetterCNN on letter_data/A, B, ..., Z")
    ap.add_argument("--data", default=DEFAULT_DATA_DIR, help="Root dir with subdirs A, B, ..., Z")
    ap.add_argument("--out", default=DEFAULT_MODEL_PATH, help="Output model path")
    ap.add_argument("--epochs", type=int, default=EPOCHS, help="Max epochs (early stop may finish sooner)")
    ap.add_argument("--lr", type=float, default=LR)
    ap.add_argument("--patience", type=int, default=EARLY_STOP_PATIENCE, help="Early stop if no val improvement")
    args = ap.parse_args()

    if not os.path.isdir(args.data):
        print(f"Data dir not found: {args.data}")
        print("Create vision/letter_data/ then run again, or run from the vision folder.")
        return 1

    # ImageFolder needs one subdir per class (A, B, ..., Z). Create them if missing.
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        os.makedirs(os.path.join(args.data, letter), exist_ok=True)

    train_transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((INPUT_SIZE, INPUT_SIZE)),
        transforms.RandomRotation(15, fill=255),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), fill=255),
        transforms.ColorJitter(brightness=0.35, contrast=0.35),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5]),
    ])
    val_transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((INPUT_SIZE, INPUT_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5]),
    ])

    train_ds = datasets.ImageFolder(args.data, transform=train_transform)
    val_ds = datasets.ImageFolder(args.data, transform=val_transform)
    n = len(train_ds)
    if n == 0:
        print("No images found in letter_data/A, B, ..., Z.")
        print("  Run process_image.py once to fill crops/, then run populate_letter_data.py to label and copy into letter_data/.")
        return 1
    # With very few images (e.g. 1 per letter), val set is tiny and val_acc is noise. Train on all.
    if n < 40:
        n_val = 0
        n_train = n
        train_sub = torch.utils.data.Subset(train_ds, range(n))
        val_subset = torch.utils.data.Subset(val_ds, [])
        print("Small dataset: training on all samples (no validation split).")
    else:
        n_val = max(1, int(n * VAL_FRAC))
        n_train = n - n_val
        train_sub, val_sub = random_split(train_ds, [n_train, n_val], generator=torch.Generator().manual_seed(42))
        val_subset = Subset(val_ds, val_sub.indices)
    batch_size = min(BATCH_SIZE, max(4, n_train))
    train_loader = DataLoader(train_sub, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_subset, batch_size=batch_size, shuffle=False, num_workers=0) if n_val > 0 else None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LetterCNN(num_classes=NUM_CLASSES).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=5)
    criterion = nn.CrossEntropyLoss()

    print(f"Training on {n_train} samples" + (f", validating on {n_val}" if n_val else " (no val split)") + f", batch_size={batch_size}. Classes: {train_ds.classes}")
    best_acc = 0.0
    epochs_no_improve = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            opt.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for x, y in train_loader:
                x, y = x.to(device), y.to(device)
                logits = model(x)
                pred = logits.argmax(dim=1)
                correct += (pred == y).sum().item()
                total += y.size(0)
        train_acc = correct / total if total else 0.0
        if val_loader is not None:
            correct, total = 0, 0
            with torch.no_grad():
                for x, y in val_loader:
                    x, y = x.to(device), y.to(device)
                    logits = model(x)
                    pred = logits.argmax(dim=1)
                    correct += (pred == y).sum().item()
                    total += y.size(0)
            val_acc = correct / total if total else 0.0
            sched.step(val_acc)
            acc = val_acc
        else:
            acc = train_acc
            sched.step(train_acc)
        if acc > best_acc:
            best_acc = acc
            epochs_no_improve = 0
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            torch.save(model.state_dict(), args.out)
            extra = f"  val_acc={acc:.2%}" if val_loader else ""
            print(f"Epoch {epoch}/{args.epochs}  train_loss={train_loss:.4f}  train_acc={train_acc:.2%}{extra}  [saved]")
        else:
            epochs_no_improve += 1
            extra = f"  val_acc={acc:.2%}" if val_loader else ""
            print(f"Epoch {epoch}/{args.epochs}  train_loss={train_loss:.4f}  train_acc={train_acc:.2%}{extra}")
        if epochs_no_improve >= args.patience:
            print(f"Early stopping (no improvement for {args.patience} epochs).")
            break

    print(f"Done. Best acc: {best_acc:.2%}. Model saved to {args.out}")


if __name__ == "__main__":
    raise SystemExit(main() or 0)
