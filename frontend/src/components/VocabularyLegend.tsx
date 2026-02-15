import {
    VOCABULARY_LEVELS,
    VOCABULARY_LEVEL_RANGES,
    getLevelColor,
} from "../utils/vocabularyLevels";

/**
 * Legend explaining vocabulary levels and frequency scale
 */
export default function VocabularyLegend() {
    const levels = [
        { key: VOCABULARY_LEVELS.BEGINNER, label: "Beginner" },
        { key: VOCABULARY_LEVELS.INTERMEDIATE, label: "Intermediate" },
        { key: VOCABULARY_LEVELS.ADVANCED, label: "Advanced" },
        { key: VOCABULARY_LEVELS.EXPERT, label: "Expert" },
        { key: VOCABULARY_LEVELS.MASTER, label: "Master" },
    ];

    return (
        <div className="mt-6 bg-white rounded-xl p-4 shadow-lg border-4 border-black">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <h4 className="font-bold mb-2">Vocabulary Levels:</h4>
                    <div className="flex flex-wrap gap-2">
                        {levels.map(({ key, label }) => (
                            <span
                                key={key}
                                className="px-2 py-1 rounded text-xs font-bold text-white"
                                style={{
                                    backgroundColor: getLevelColor(key),
                                }}
                            >
                                {label} ({VOCABULARY_LEVEL_RANGES[key]})
                            </span>
                        ))}
                    </div>
                </div>
                <div>
                    <h4 className="font-bold mb-2">Word Frequency (Zipf Scale):</h4>
                    <p className="text-sm text-gray-600">
                        Higher scores = more common words. Lower scores = rarer,
                        more advanced vocabulary. Scale ranges from 0 (very rare) to
                        8 (very common).
                    </p>
                </div>
            </div>
        </div>
    );
}
