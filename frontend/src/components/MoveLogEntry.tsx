import { getFrequencyColor } from "../utils/vocabularyLevels";

interface MoveLogEntryProps {
    timestamp: number;
    studentName: string;
    word: string;
    frequencyScore: number;
}

/**
 * Individual move log entry displaying a student's word play
 */
export default function MoveLogEntry({
    timestamp,
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

    return (
        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border-2 border-gray-200 hover:bg-gray-100 transition-colors">
            <span className="text-sm text-gray-500 min-w-[60px]">
                {formattedTime}
            </span>
            <span className="font-semibold text-gray-900 min-w-[80px]">
                {studentName}
            </span>
            <span className="text-gray-600">played</span>
            <span className="font-bold text-lg">"{word}"</span>
            <span
                className="ml-auto px-3 py-1 rounded-full text-sm font-bold text-white"
                style={{ backgroundColor: getFrequencyColor(frequencyScore) }}
            >
                {frequencyScore.toFixed(1)}
            </span>
        </div>
    );
}
