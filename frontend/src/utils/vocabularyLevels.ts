/**
 * Vocabulary level utilities and constants
 *
 * Maps average Zipf word frequency to approximate elementary grade reading levels.
 * Calibrated against word_frequencies.json:
 *   Pre-K sight words (the, big, see, run)       → Zipf ~5.5–7.7
 *   Kindergarten (cat, dog, mom, hat, sun)        → Zipf ~4.8–5.5
 *   1st Grade (happy, water, friend, school)      → Zipf ~4.7–5.7
 *   2nd Grade (beautiful, ocean, forest, excited)  → Zipf ~4.4–5.2
 *   3rd Grade (adventure, curious, enormous)       → Zipf ~4.2–4.9
 *   4th Grade (spectacular, reluctant, investigate) → Zipf ~3.8–4.9
 *   5th Grade (consequence, elaborate, obstacle)    → Zipf ~3.5–4.3
 *   6th Grade+ (hypothesis, meticulous, ambiguous)  → Zipf ~3.0–4.1
 */

export type VocabularyLevel =
    | "pre-k"
    | "kindergarten"
    | "1st-grade"
    | "2nd-grade"
    | "3rd-grade"
    | "4th-grade"
    | "5th-grade"
    | "6th-grade+";

export const VOCABULARY_LEVELS = {
    PRE_K: "pre-k" as VocabularyLevel,
    KINDERGARTEN: "kindergarten" as VocabularyLevel,
    FIRST_GRADE: "1st-grade" as VocabularyLevel,
    SECOND_GRADE: "2nd-grade" as VocabularyLevel,
    THIRD_GRADE: "3rd-grade" as VocabularyLevel,
    FOURTH_GRADE: "4th-grade" as VocabularyLevel,
    FIFTH_GRADE: "5th-grade" as VocabularyLevel,
    SIXTH_GRADE_PLUS: "6th-grade+" as VocabularyLevel,
};

export const VOCABULARY_LEVEL_COLORS: Record<VocabularyLevel, string> = {
    "pre-k": "#a3c8db",      // Sky shallows
    kindergarten: "#92b9ce",  // Light surf
    "1st-grade": "#82aac0",   // Shallow water
    "2nd-grade": "#719bb3",   // Wading depth
    "3rd-grade": "#618ca6",   // Mid ocean
    "4th-grade": "#507d99",   // Deep water
    "5th-grade": "#3f6e8c",   // Ocean depths
    "6th-grade+": "#2d5f7f",  // Deep wave
};

export const VOCABULARY_LEVEL_RANGES: Record<VocabularyLevel, string> = {
    "pre-k": "≥ 5.6",
    kindergarten: "5.2 – 5.6",
    "1st-grade": "4.8 – 5.2",
    "2nd-grade": "4.5 – 4.8",
    "3rd-grade": "4.2 – 4.5",
    "4th-grade": "3.9 – 4.2",
    "5th-grade": "3.6 – 3.9",
    "6th-grade+": "< 3.6",
};

export const VOCABULARY_LEVEL_LABELS: Record<VocabularyLevel, string> = {
    "pre-k": "Pre-K",
    kindergarten: "Kindergarten",
    "1st-grade": "1st Grade",
    "2nd-grade": "2nd Grade",
    "3rd-grade": "3rd Grade",
    "4th-grade": "4th Grade",
    "5th-grade": "5th Grade",
    "6th-grade+": "6th Grade+",
};

/**
 * Determine vocabulary level from average Zipf frequency.
 * Lower average frequency = student is using rarer, higher-grade words.
 */
export function getVocabularyLevel(avgFrequency: number): VocabularyLevel {
    if (avgFrequency >= 5.6) return "pre-k";
    if (avgFrequency >= 5.2) return "kindergarten";
    if (avgFrequency >= 4.8) return "1st-grade";
    if (avgFrequency >= 4.5) return "2nd-grade";
    if (avgFrequency >= 4.2) return "3rd-grade";
    if (avgFrequency >= 3.9) return "4th-grade";
    if (avgFrequency >= 3.6) return "5th-grade";
    return "6th-grade+";
}

/**
 * Get color for a vocabulary level
 */
export function getLevelColor(level: string): string {
    return (
        VOCABULARY_LEVEL_COLORS[level as VocabularyLevel] ||
        VOCABULARY_LEVEL_COLORS["pre-k"]
    );
}

/**
 * Get display label for a vocabulary level
 */
export function getLevelLabel(level: string): string {
    return VOCABULARY_LEVEL_LABELS[level as VocabularyLevel] || level;
}

/**
 * Get color for a word frequency score (Zipf scale)
 * Light = common/shallow, Dark = rare/deep ocean
 */
export function getFrequencyColor(freq: number): string {
    if (freq >= 5.6) return "#a3c8db"; // Sky shallows
    if (freq >= 5.2) return "#92b9ce"; // Light surf
    if (freq >= 4.8) return "#82aac0"; // Shallow water
    if (freq >= 4.5) return "#719bb3"; // Wading depth
    if (freq >= 4.2) return "#618ca6"; // Mid ocean
    if (freq >= 3.9) return "#507d99"; // Deep water
    if (freq >= 3.6) return "#3f6e8c"; // Ocean depths
    return "#2d5f7f";                  // Deep wave
}
