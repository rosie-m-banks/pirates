import { useEffect, useState } from "react";
import MoveLog from "./components/MoveLog";
import PlayerStatistics from "./components/PlayerStatistics";
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
        <div className="w-full max-w-7xl mx-auto px-4 flex flex-col gap-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {imageUrl && (
                    <div className="flex flex-col justify-center">
                        <img
                            src={imageUrl}
                            alt="Game board"
                            className="max-w-full h-auto rounded-lg border-2"
                            style={{
                                maxHeight: "600px",
                                borderColor: "var(--sand-dark)",
                            }}
                        />
                        {imageTimestamp && (
                            <span
                                className="text-sm font-semibold"
                                style={{ color: "var(--ocean-dark)" }}
                            >
                                Last updated:{" "}
                                {new Date(imageTimestamp).toLocaleTimeString()}
                            </span>
                        )}
                    </div>
                )}
                <MoveLog
                    entries={moveLog}
                    isLoading={isLoading}
                    error={error}
                />
            </div>

            <PlayerStatistics
                players={gameData.players}
                playerStats={playerStats}
                getStudentName={getStudentName}
            />
        </div>
    );
}

// Re-export type for convenience
export type { TeacherGameData } from "./types/stats";
