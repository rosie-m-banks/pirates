# Letter templates for Bananagram tiles

Recognition is **template-only**: each tile crop is compared to reference images A.png through Z.png. For consistent results, these must be from **your actual Bananagram tiles**.

## One-time setup

1. **Capture tiles**  
   Run `process_image.py` once. It will detect tiles, save crops to `vision/crops/`, and report "unknown" for all letters (no templates yet).

2. **Build templates**  
   Run `build_templates.py` from the `vision` folder:
   ```bash
   cd vision
   python build_templates.py
   ```
   For each crop image you'll be shown the tile and asked for its letter (A–Z) or Enter to skip. Each answer is saved as `templates/<letter>.png`. You only need one crop per letter (e.g. one "A", one "B", …). You can run it again and overwrite to improve a template.

3. **Run again**  
   Run `process_image.py` again. It will load the templates and recognize letters by matching crops to these references.

## File names

- **A.png** … **Z.png** — one image per letter (grayscale or color; converted to grayscale). Use cropped tile images that show a single letter.

## How matching works

Every crop and every template is normalized the same way: center region (letter only), binarized (letter black, background white), letter centered in a 64×64 image. The pipeline tries four rotations and both polarities, then picks the best-matching template. No OCR models are used.
