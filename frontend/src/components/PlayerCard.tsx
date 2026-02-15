import { getLevelColor } from "../utils/vocabularyLevels";
import type { PlayerStats } from "../types/stats";

interface PlayerCardProps {
    studentName: string;
    currentWords: number;
    stats?: PlayerStats;
}

/**
 * Individual player card showing vocabulary statistics
 */
export default function PlayerCard({
    studentName,
    currentWords,
    stats,
}: PlayerCardProps) {
    return (
        <div className="bg-gray-50 rounded-lg p-4 border-2 border-gray-300">
            <div className="flex items-center justify-between mb-2">
                <h4 className="text-xl font-bold">{studentName}</h4>
                {stats && (
                    <span
                        className="px-3 py-1 rounded-full text-xs font-bold text-white"
                        style={{
                            backgroundColor: getLevelColor(
                                stats.vocabularyLevel,
                            ),
                        }}
                    >
                        {stats.vocabularyLevel.toUpperCase()}
                    </span>
                )}
            </div>

            <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                    <div className="text-3xl font-bold text-blue-600">
                        {currentWords}
                    </div>
                    <div className="text-sm text-gray-600">Current Words</div>
                </div>
                <div>
                    <div className="text-3xl font-bold text-green-600">
                        {stats?.totalWords || 0}
                    </div>
                    <div className="text-sm text-gray-600">Total Words</div>
                </div>
                <div>
                    <div className="text-3xl font-bold text-purple-600">
                        {stats?.avgWordFrequency.toFixed(1) || "0.0"}
                    </div>
                    <div className="text-sm text-gray-600">Avg Frequency</div>
                </div>
            </div>
        </div>
    );
}
