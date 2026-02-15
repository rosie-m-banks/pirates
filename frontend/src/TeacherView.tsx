import { useEffect, useState } from "react";
import MoveLog from "./components/MoveLog";
import PlayerStatistics from "./components/PlayerStatistics";
import VocabularyLegend from "./components/VocabularyLegend";
import { useMoveLog } from "./hooks/useMoveLog";
import { useGameImage } from "./hooks/useGameImage";
import type { TeacherGameData, PlayerStats } from "./types/stats";

const STUDENT_NAMES = [
    "Alice",
    "Bob",
    "Carol",
    "David",
    "Emma",
    "Frank",
    "Grace",
    "Henry",
] as const;

export function getStudentName(index: number): string {
    return STUDENT_NAMES[index] || `Student ${index + 1}`;
}

interface TeacherViewProps {
    gameData: TeacherGameData;
}

/**
 * Teacher Dashboard - Monitor student vocabulary progress in real-time
 *
 * Features:
 * - Full move log loaded from backend (single source of truth)
 * - Real-time updates via dedicated WebSocket events ('move-log', 'image')
 * - Backend handles all log logic; frontend only displays
 * - Player statistics and vocabulary levels
 * - Live game board image display
 */
export default function TeacherView({ gameData }: TeacherViewProps) {
    const { moveLog, isLoading, error } = useMoveLog();
    const { imageUrl, timestamp: imageTimestamp } = useGameImage();
    const [playerStats, setPlayerStats] = useState<Map<number, PlayerStats>>(
        new Map(),
    );

    // Update player statistics from analytics
    useEffect(() => {
        if (!gameData._analytics?.vocabularyStats?.players) return;

        const newStats = new Map<number, PlayerStats>();
        gameData._analytics.vocabularyStats.players.forEach((stats) => {
            const playerIndex = parseInt(stats.playerId.split("_")[1]);
            newStats.set(playerIndex, stats);
        });
        setPlayerStats(newStats);
    }, [gameData._analytics]);

    return (
        <div className="w-full max-w-7xl mx-auto px-4">
            <header className="mb-8 text-center">
                <h2
                    className="text-4xl font-bold mb-2"
                    style={{ fontFamily: "FatPix, sans-serif" }}
                >
                    👨‍🏫 Teacher Dashboard
                </h2>
                <p className="text-gray-600">
                    Monitor student vocabulary progress in real-time
                </p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <PlayerStatistics
                    players={gameData.players}
                    playerStats={playerStats}
                    getStudentName={getStudentName}
                />
                <MoveLog
                    entries={moveLog}
                    isLoading={isLoading}
                    error={error}
                />
            </div>

            {imageUrl && (
                <div className="mt-6 bg-white rounded-xl p-6 shadow-lg border-4 border-black">
                    <div className="flex items-center gap-3 mb-4">
                        <h3 className="text-2xl font-bold">🎮 Game Board</h3>
                        {imageTimestamp && (
                            <span className="text-sm text-gray-500">
                                Last updated:{" "}
                                {new Date(imageTimestamp).toLocaleTimeString()}
                            </span>
                        )}
                    </div>
                    <div className="flex justify-center">
                        <img
                            src={imageUrl}
                            alt="Game board"
                            className="max-w-full h-auto rounded-lg border-2 border-gray-300"
                            style={{ maxHeight: "600px" }}
                        />
                    </div>
                </div>
            )}

            <VocabularyLegend />
        </div>
    );
}

// Re-export type for convenience
export type { TeacherGameData } from "./types/stats";
