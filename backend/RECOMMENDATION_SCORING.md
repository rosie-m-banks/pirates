# Recommendation Scoring System

This document explains how to customize the word recommendation scoring system.

## Overview

The scoring system filters and ranks recommended words based on:
1. **Word Frequency** (zipf scale 0-8, from corpus data)
2. **Word Length** (number of characters)

## Quick Start

### Default Behavior
- **Filters out** words with frequency < 1.0 (extremely rare words)
- **Prioritizes** longer words that are relatively common
- Formula: `score = (frequency / 8) * 1.0 + length * 2.0`

### Test the System
```bash
node test-recommendations.js
```

## Customization Guide

All customization happens in `backend/recommendationScorer.js`.

### 1. Adjust Filtering Threshold

**Where:** `ScoringConfig.minFrequency`

```javascript
// More permissive (include rare words)
minFrequency: 0.5,  // Include uncommon words

// More restrictive (only common words)
minFrequency: 3.0,  // Only fairly common words
minFrequency: 5.0,  // Only common words
```

**Frequency Reference:**
- 0-1: Extremely rare (technical terms, typos)
- 1-3: Uncommon (xylophone, aardvark)
- 3-5: Fairly common (elephant, running)
- 5-7: Common (cat, dog, run)
- 7-8: Very common (the, and, is)

### 2. Change Score Weights

**Where:** `ScoringConfig.weights`

```javascript
// Prioritize length over frequency (longer words first)
weights: {
  frequency: 0.5,
  length: 3.0,
}

// Prioritize frequency over length (common words first)
weights: {
  frequency: 3.0,
  length: 0.5,
}

// Balanced (default)
weights: {
  frequency: 1.0,
  length: 2.0,
}
```

### 3. Use Pre-Built Strategies

**Where:** Import from `ScoringStrategies`

```javascript
// In worker.js, replace ScoringConfig with:
import { ScoringStrategies } from './recommendationScorer.js';

// Then in the message handler:
result.recommended_words = sortRecommendations(
  result.recommended_words,
  frequencies,
  ScoringStrategies.longestFirst  // or .mostCommonFirst, .balanced, .commonAndLong
);
```

**Available Strategies:**
- `balanced` - Good mix of common and long words (default)
- `longestFirst` - Prioritize longest words
- `mostCommonFirst` - Prioritize most frequent words
- `commonAndLong` - Only very common words (freq ≥ 5), prioritize length

### 4. Change Scoring Strategy

**Where:** `ScoringConfig.strategy`

```javascript
// Additive (default): weighted sum
strategy: 'additive',
// score = freq_weight * freq + len_weight * len

// Multiplicative: emphasize both factors
strategy: 'multiplicative',
// score = freq^freq_weight * len^len_weight

// Custom: your own logic
strategy: 'custom',
// Edit customScoringFunction() in recommendationScorer.js
```

### 5. Enable Normalization

**Where:** `ScoringConfig.normalize`

```javascript
normalize: {
  frequency: true,   // Scale frequency (0-8) to (0-1)
  length: false,     // Keep length as raw value (3-15)
}
```

Normalization helps when using multiplicative strategy or comparing different scales.

## Examples

### Example 1: Only suggest common, long words

```javascript
export const ScoringConfig = {
  minFrequency: 5.0,           // Only common words
  weights: {
    frequency: 1.0,
    length: 3.0,               // Strong preference for length
  },
  strategy: 'additive',
  normalize: { frequency: true, length: false },
};
```

### Example 2: Suggest rare but valid words

```javascript
export const ScoringConfig = {
  minFrequency: 0.5,           // Include uncommon words
  weights: {
    frequency: 0.3,            // Don't care much about frequency
    length: 2.5,               // Care more about length
  },
  strategy: 'additive',
  normalize: { frequency: true, length: false },
};
```

### Example 3: Custom scoring with bonuses

```javascript
export const ScoringConfig = {
  minFrequency: 1.0,
  weights: { frequency: 1.0, length: 2.0 },
  strategy: 'custom',          // Uses customScoringFunction
  normalize: { frequency: true, length: false },
};

// Then edit customScoringFunction in recommendationScorer.js:
function customScoringFunction(word, frequency, length, config) {
  let score = config.weights.frequency * frequency + config.weights.length * length;

  // Bonus for 7+ letter words
  if (length >= 7) score += 3;

  // Bonus for words with 'q' or 'z' (high value in Scrabble)
  if (word.includes('q') || word.includes('z')) score += 2;

  return score;
}
```

## Architecture

```
worker.js
  └─> processGameState()         [finds all valid words]
       └─> recommended_words     [unsorted object]
            └─> sortRecommendations()    [filters & sorts]
                 ├─> filters by minFrequency
                 ├─> calculates score for each word
                 └─> returns sorted object
```

## Tips

1. **Test after changes**: Run `node test-recommendations.js` to see effects
2. **Start conservative**: Begin with default config, then adjust incrementally
3. **Monitor performance**: Scoring adds ~1-2ms per 100 words (negligible)
4. **Consider your game**: Adjust based on whether longer words are more valuable

## Files

- `recommendationScorer.js` - Main scoring logic (edit this)
- `worker.js` - Loads frequencies and applies scoring
- `test-recommendations.js` - Test scoring with sample words
- `data/word_frequencies.json` - Pre-computed frequency data (2.8MB)

## Regenerating Frequencies

If you need to regenerate the frequency file:

```bash
cd backend/scripts
source venv/bin/activate
python3 generate_word_frequencies.py
```

This takes ~3-5 minutes for 178k words.
