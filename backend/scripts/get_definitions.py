import json
import time
from pathlib import Path
from nltk.corpus import wordnet as wn

# Load existing definitions if file exists
defs = {}
output_file = Path('output.json')
if output_file.exists():
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            defs = json.load(f)
            print(f"Loaded {len(defs)} existing definitions")
    except:
        pass

def get_definition(word):
    """Get short definition from WordNet (local database, no rate limits)"""
    try:
        synsets = wn.synsets(word)
        if synsets:
            # Get the first (most common) synset's definition
            definition = synsets[0].definition()
            # Truncate if too long
            if len(definition) > 200:
                definition = definition[:197] + "..."
            return definition
    except:
        pass
    return None

try:
    with open('../data/words.txt', 'r', encoding='utf-8') as file:
        words = [line.strip().lower() for line in file if line.strip()]
    
    # Filter out words we already have
    words_to_process = [w for w in words if w not in defs]
    print(f"Processing {len(words_to_process)} words (skipping {len(words) - len(words_to_process)} already done)")
    
    total = len(words_to_process)
    if total == 0:
        print("No words to process!")
    else:
        start_time = time.time()
        
        for i, word in enumerate(words_to_process, 1):
            definition = get_definition(word)
            if definition:
                defs[word] = definition
            
            # Show progress every 1000 words
            if i % 1000 == 0 or i == total:
                found_count = len([w for w in words_to_process[:i] if w in defs])
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (total - i) / rate if rate > 0 else 0
                print(f"Progress: {i}/{total} ({i*100//total}%) | "
                      f"Found: {found_count} | Rate: {rate:.0f} words/sec | ETA: {remaining/60:.1f} min")
            
            # Save progress every 5000 words
            if i % 5000 == 0:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(defs, f, ensure_ascii=False, indent=4)
                print(f"  Progress saved ({len(defs)} definitions so far)")

except FileNotFoundError:
    print("Error: The file was not found.")
except LookupError:
    print("Error: NLTK WordNet data not found.")
    print("Please run: python -m nltk.downloader wordnet")
    print("Or in Python: import nltk; nltk.download('wordnet')")

# Final save
with open(output_file, 'w', encoding='utf-8') as json_file:
    json.dump(defs, json_file, ensure_ascii=False, indent=4)

print(f"\nSaved {len(defs)} definitions to output.json")
