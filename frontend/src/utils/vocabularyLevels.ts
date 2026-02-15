/**
 * Vocabulary level utilities and constants
 */

export type VocabularyLevel = "beginner" | "intermediate" | "advanced" | "expert" | "master";

export const VOCABULARY_LEVELS = {
    BEGINNER: "beginner" as VocabularyLevel,
    INTERMEDIATE: "intermediate" as VocabularyLevel,
    ADVANCED: "advanced" as VocabularyLevel,
    EXPERT: "expert" as VocabularyLevel,
    MASTER: "master" as VocabularyLevel,
};

export const VOCABULARY_LEVEL_COLORS: Record<VocabularyLevel, string> = {
    beginner: "#94a3b8",
    intermediate: "#60a5fa",
    advanced: "#8b5cf6",
    expert: "#f59e0b",
    master: "#ef4444",
};

export const VOCABULARY_LEVEL_RANGES: Record<VocabularyLevel, string> = {
    beginner: "≥6.0",
    intermediate: "5-6",
    advanced: "4-5",
    expert: "3-4",
    master: "<3",
};

/**
 * Get color for a vocabulary level
 */
export function getLevelColor(level: string): string {
    return VOCABULARY_LEVEL_COLORS[level as VocabularyLevel] || VOCABULARY_LEVEL_COLORS.beginner;
}

/**
 * Get color for a word frequency score (Zipf scale)
 * Higher = more common = green, Lower = rare = red
 */
export function getFrequencyColor(freq: number): string {
    if (freq >= 6) return "#10b981"; // Green - very common
    if (freq >= 5) return "#3b82f6"; // Blue - common
    if (freq >= 4) return "#8b5cf6"; // Purple - less common
    if (freq >= 3) return "#f59e0b"; // Orange - rare
    return "#ef4444"; // Red - very rare
}
