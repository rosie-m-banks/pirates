import { getFrequencyColor } from "../utils/vocabularyLevels";
import { PLAYER_COLORS } from "../StudentView";

interface MoveLogEntryProps {
    timestamp: number;
    playerIndex: number;
    studentName: string;
    word: string;
    frequencyScore: number;
}

/**
 * Individual move log entry displaying a student's word play
 */
export default function MoveLogEntry({
    timestamp,
    playerIndex,
    studentName,
    word,
    frequencyScore,
}: MoveLogEntryProps) {
    const formattedTime = new Date(timestamp).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    });

    const colorScheme = PLAYER_COLORS[playerIndex % PLAYER_COLORS.length];

    return (
        <div
            className="flex items-center gap-3 p-3 rounded-lg border-l-4 border-2 transition-colors"
            style={{
                backgroundColor: colorScheme.bg + "22",
                borderLeftColor: colorScheme.border,
                borderColor: colorScheme.border,
                borderLeftWidth: "6px",
            }}
        >
            <span
                className="text-sm font-semibold min-w-[60px]"
                style={{ color: "var(--wave-color)" }}
            >
                {formattedTime}
            </span>
            <span
                className="font-bold min-w-[80px]"
                style={{ color: colorScheme.border }}
            >
                {studentName}
            </span>
            <span style={{ color: "var(--ocean-dark)" }}>played</span>
            <span className="font-bold text-lg text-black">"{word}"</span>
            <span className="ml-auto px-3 py-1 text-sm font-bold text-white/70">
                {frequencyScore.toFixed(1)}
            </span>
        </div>
    );
}
