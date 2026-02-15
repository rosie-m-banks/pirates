/**
 * Modular recommendation scoring system for word suggestions.
 * Allows easy customization of how words are filtered and ranked.
 */

/**
 * Configuration for recommendation scoring.
 * Adjust these values to change recommendation behavior without touching core logic.
 */
export const ScoringConfig = {
    // Minimum frequency threshold (zipf scale 0-8). Words below this are filtered out.
    // 0 = extremely rare, 3 = uncommon, 5 = common, 7+ = very common
    minFrequency: 1.0,

    // Weights for combining frequency and length into a final score
    weights: {
        frequency: 1.5, // How much to value word frequency (higher = prefer common words)
        length: 1.0, // How much to value word length (higher = prefer longer words)
    },

    // Scoring strategy: 'additive', 'multiplicative', or 'custom'
    strategy: "additive",

    // For 'additive' strategy, you can normalize scores to comparable scales
    normalize: {
        frequency: true, // Normalize frequency (0-8 range) to 0-1
        length: true, // Keep length as raw value (typically 3-15)
    },
};

/**
 * Score a single word based on frequency and length.
 * @param {string} word - The word to score
 * @param {number} frequency - Word frequency (zipf scale 0-8)
 * @param {object} config - Scoring configuration (defaults to ScoringConfig)
 * @returns {number} - Score (higher = better recommendation)
 */
export function scoreWord(word, frequency, config = ScoringConfig) {
    const length = word.length;

    // Normalize values if configured
    const normalizedFreq = config.normalize.frequency
        ? frequency / 8.0
        : frequency;
    const normalizedLength = config.normalize.length ? length / 15.0 : length;

    // Apply scoring strategy
    switch (config.strategy) {
        case "multiplicative":
            // Multiplicative: good for emphasizing both factors (freq * length)
            return (
                Math.pow(normalizedFreq, config.weights.frequency) *
                Math.pow(normalizedLength, config.weights.length)
            );

        case "additive":
            // Additive: weighted sum (default, easy to understand)
            return (
                config.weights.frequency * normalizedFreq +
                config.weights.length * normalizedLength
            );

        case "custom":
            // Custom: plug in your own scoring function here
            return customScoringFunction(word, frequency, length, config);

        default:
            throw new Error(`Unknown scoring strategy: ${config.strategy}`);
    }
}

/**
 * Custom scoring function - modify this for special scoring rules.
 * Example: bonus for words ending in certain letters, penalties for rare patterns, etc.
 */
function customScoringFunction(word, frequency, length, config) {
    // Example custom logic:
    let score =
        config.weights.frequency * frequency + config.weights.length * length;

    // Bonus for words 6+ letters long
    if (length >= 6) score += 2;

    // Bonus for words ending in common suffixes
    if (word.endsWith("ing") || word.endsWith("ed") || word.endsWith("er")) {
        score += 1;
    }

    return score;
}

/**
 * Filter and sort recommended words by score.
 * @param {Object} recommendedWords - Map of word -> construction array
 * @param {Object} frequencies - Map of word -> frequency score
 * @param {object} config - Scoring configuration (defaults to ScoringConfig)
 * @returns {Object} - Sorted map of word -> { construction, score, frequency, length }
 */
export function sortRecommendations(
    recommendedWords,
    frequencies,
    config = ScoringConfig,
) {
    const words = Object.keys(recommendedWords);

    // Step 1: Filter out infrequent words
    const filteredWords = words.filter((word) => {
        const freq = frequencies[word] || 0;
        return freq >= config.minFrequency;
    });

    // Step 2: Calculate scores for each word
    const scoredWords = filteredWords.map((word) => {
        const frequency = frequencies[word] || 0;
        const score = scoreWord(word, frequency, config);

        return {
            word,
            score,
            frequency,
            length: word.length,
            construction: recommendedWords[word],
        };
    });

    // Step 3: Sort by score (descending - highest first)
    scoredWords.sort((a, b) => b.score - a.score);

    // Step 4: Rebuild as ordered object
    const sortedRecommendedWords = {};
    for (const item of scoredWords) {
        sortedRecommendedWords[item.word] = item.construction;
    }

    return sortedRecommendedWords;
}

/**
 * Alternative scoring strategies you can swap in.
 * Import and assign to ScoringConfig.strategy to use.
 */
export const ScoringStrategies = {
    // Prefer longest words, frequency is secondary
    longestFirst: {
        minFrequency: 1.0,
        weights: { frequency: 0.5, length: 3.0 },
        strategy: "additive",
        normalize: { frequency: true, length: false },
    },

    // Prefer most common words, length is secondary
    mostCommonFirst: {
        minFrequency: 1.0,
        weights: { frequency: 3.0, length: 0.5 },
        strategy: "additive",
        normalize: { frequency: false, length: false },
    },

    // Balanced approach (default)
    balanced: {
        minFrequency: 1.0,
        weights: { frequency: 1.5, length: 1.0 },
        strategy: "additive",
        normalize: { frequency: true, length: true },
    },

    // Only show very common words (5+), prioritize length
    commonAndLong: {
        minFrequency: 5.0,
        weights: { frequency: 1.0, length: 3.0 },
        strategy: "additive",
        normalize: { frequency: true, length: false },
    },
};

/**
 * Helper: Get scoring stats for debugging/tuning.
 * Shows distribution of scores, frequencies, and lengths.
 */
export function getScoreStats(
    recommendedWords,
    frequencies,
    config = ScoringConfig,
) {
    const words = Object.keys(recommendedWords);
    const scores = words.map((word) =>
        scoreWord(word, frequencies[word] || 0, config),
    );

    return {
        count: words.length,
        scores: {
            min: Math.min(...scores),
            max: Math.max(...scores),
            avg: scores.reduce((a, b) => a + b, 0) / scores.length,
        },
        frequencies: {
            min: Math.min(...words.map((w) => frequencies[w] || 0)),
            max: Math.max(...words.map((w) => frequencies[w] || 0)),
            avg:
                words.reduce((sum, w) => sum + (frequencies[w] || 0), 0) /
                words.length,
        },
        lengths: {
            min: Math.min(...words.map((w) => w.length)),
            max: Math.max(...words.map((w) => w.length)),
            avg: words.reduce((sum, w) => sum + w.length, 0) / words.length,
        },
    };
}
