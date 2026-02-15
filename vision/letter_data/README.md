# Training data for LetterCNN

Put labeled tile crops here so the model can learn your tiles.

## Layout

Create one folder per letter (A through Z). Put any number of images of that letter in each folder:

```
letter_data/
  A/    <- all images of "A" tiles
  B/    <- all images of "B" tiles
  ...
  Z/
```

You can have multiple images per letter; more (and more varied) is better. Use the same crop format as the main pipeline (e.g. copy from `crops/` after running `process_image.py`, then move into the right letter folder).

## How to populate

1. Run `process_image.py` once so `crops/` is filled with tile images.
2. Run `python populate_letter_data.py`: for each crop you'll be shown the image and asked for its letter (A–Z). Images are copied into `letter_data/A`, `letter_data/B`, etc. You can run it again on new crops to add more samples.
3. Alternatively, create folders `letter_data/A` … `letter_data/Z` and copy/move images from `crops/` into the right folder by hand.
4. Aim for at least 5–10 images per letter; 20+ per letter gives better accuracy and robustness.

## Train

From the `vision` directory:

```bash
python train_letter_model.py
```

Optional: `--data ./letter_data`, `--out ./models/letter_cnn.pt`, `--epochs 50`.

After training, `process_image.py` will use the CNN automatically when `models/letter_cnn.pt` exists.
