import { useEffect, useState } from "react";
import MoveLog from "./components/MoveLog";
import PlayerStatistics from "./components/PlayerStatistics";
import VocabularyLegend from "./components/VocabularyLegend";
import { useMoveLog } from "./hooks/useMoveLog";
import type { TeacherGameData, PlayerStats } from "./types/teacher";

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

function getStudentName(index: number): string {
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
 * - Real-time updates via WebSocket
 * - Automatic deduplication of moves
 * - Player statistics and vocabulary levels
 */
export default function TeacherView({ gameData }: TeacherViewProps) {
    const { moveLog, addMoves, isLoading, error } = useMoveLog();
    const [playerStats, setPlayerStats] = useState<Map<number, PlayerStats>>(
        new Map(),
    );

    // Process new moves from game data
    useEffect(() => {
        if (!gameData.move) return;

        const newEntries = gameData.move.players.flatMap((player) =>
            player.addedWords.map((wordPlay) => ({
                id: `${gameData.move!.timestamp}-${player.playerIndex}-${wordPlay.word}`,
                timestamp: gameData.move!.timestamp,
                studentName: getStudentName(player.playerIndex),
                word: wordPlay.word,
                frequencyScore: wordPlay.frequencyScore,
            })),
        );

        if (newEntries.length > 0) {
            addMoves(newEntries);
        }
    }, [gameData.move, addMoves]);

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

            <VocabularyLegend />
        </div>
    );
}

// Re-export type for convenience
export type { TeacherGameData } from "./types/teacher";
