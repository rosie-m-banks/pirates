import { getLevelColor, getLevelLabel } from "../utils/vocabularyLevels";
import { PLAYER_COLORS } from "../StudentView";
import type { PlayerStats } from "../types/stats";

interface PlayerCardProps {
    playerIndex: number;
    studentName: string;
    currentWords: number;
    stats?: PlayerStats;
}

/**
 * Individual player card showing vocabulary statistics
 */
export default function PlayerCard({
    playerIndex,
    studentName,
    currentWords,
    stats,
}: PlayerCardProps) {
    const colorScheme = PLAYER_COLORS[playerIndex % PLAYER_COLORS.length];

    return (
        <div
            className="rounded-lg p-4 border-2 border-l-4"
            style={{
                backgroundColor: colorScheme.bg + "22",
                borderColor: colorScheme.border,
                borderBottomWidth: "6px",
                borderBottomColor: colorScheme.border,
                borderLeftColor: colorScheme.border,
            }}
        >
            <div className="flex items-center justify-between mb-2">
                <h4
                    className="text-xl font-bold"
                    style={{ color: colorScheme.border }}
                >
                    {studentName}
                </h4>
                {stats && (
                    <span
                        className="px-3 py-1 rounded-full text-xs font-bold text-white shadow-[2px_3px_0px_rgba(0,0,0)]"
                        style={{
                            backgroundColor: getLevelColor(
                                stats.vocabularyLevel,
                            ),
                        }}
                    >
                        {getLevelLabel(stats.vocabularyLevel)}
                    </span>
                )}
            </div>

            <div className="grid grid-cols-3 gap-4 text-center text-gray-700">
                <div>
                    <div className="text-3xl font-bold">{currentWords}</div>
                    <div
                        className="text-sm font-semibold"
                        style={{ color: "var(--wave-color)" }}
                    >
                        Current Words
                    </div>
                </div>
                <div>
                    <div className="text-3xl font-bold">
                        {stats?.totalWords || 0}
                    </div>
                    <div
                        className="text-sm font-semibold"
                        style={{ color: "var(--wave-color)" }}
                    >
                        Total Words
                    </div>
                </div>
                <div>
                    <div className="text-3xl font-bold">
                        {stats?.avgWordFrequency.toFixed(1) || "0.0"}
                    </div>
                    <div
                        className="text-sm font-semibold"
                        style={{ color: "var(--wave-color)" }}
                    >
                        Avg Complexity
                    </div>
                </div>
            </div>
        </div>
    );
}
