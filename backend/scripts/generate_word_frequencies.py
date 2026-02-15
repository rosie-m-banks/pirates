#!/usr/bin/env python3
"""
Generate word frequency scores for the game dictionary.
Uses wordfreq's zipf_frequency (scale 0-8, higher = more common).
Words not in wordfreq get score 0.0 (uncommon).
"""

import json
import sys
from pathlib import Path

try:
    from wordfreq import zipf_frequency
except ImportError:
    print("Error: wordfreq not installed. Install with: pip install wordfreq", file=sys.stderr)
    sys.exit(1)


def generate_frequencies(words_file, output_file):
    """Read dictionary and generate frequency scores."""
    words_path = Path(words_file)

    if not words_path.exists():
        print(f"Error: {words_file} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Reading dictionary from {words_file}...")
    with open(words_path, 'r', encoding='utf-8') as f:
        words = [line.strip().lower() for line in f if line.strip()]

    print(f"Processing {len(words)} words...")
    frequencies = {}

    # Use 'en' (English) as the language
    for i, word in enumerate(words):
        if i % 10000 == 0:
            print(f"  Processed {i}/{len(words)} words...")

        # Get zipf frequency (0-8 scale, higher = more common)
        # Common words: 5-8, uncommon: 1-3, very rare: 0
        freq = zipf_frequency(word, 'en', wordlist='large')
        frequencies[word] = round(freq, 2)

    print(f"\nWriting frequencies to {output_file}...")
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(frequencies, f, separators=(',', ':'))

    # Print statistics
    total = len(frequencies)
    with_freq = sum(1 for f in frequencies.values() if f > 0)
    print(f"\nComplete!")
    print(f"  Total words: {total}")
    print(f"  Words with frequency > 0: {with_freq} ({100*with_freq/total:.1f}%)")
    print(f"  Words with no frequency: {total - with_freq} ({100*(total-with_freq)/total:.1f}%)")

    # Show some examples
    print("\nExample frequencies:")
    examples = ['the', 'cat', 'dog', 'run', 'hello', 'xylophone', 'zephyr']
    for word in examples:
        if word in frequencies:
            print(f"  {word}: {frequencies[word]}")


if __name__ == '__main__':
    words_file = '../data/words.txt'
    output_file = '../data/word_frequencies.json'

    # Allow command line override
    if len(sys.argv) >= 2:
        words_file = sys.argv[1]
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]

    generate_frequencies(words_file, output_file)
