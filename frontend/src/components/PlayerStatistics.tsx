import PlayerCard from "./PlayerCard";
import type { PlayerStats, Player } from "../types/stats";

interface PlayerStatisticsProps {
    players: Player[];
    playerStats: Map<number, PlayerStats>;
    getStudentName: (index: number) => string;
}

/**
 * Container for all player statistics cards
 */
export default function PlayerStatistics({
    players,
    playerStats,
    getStudentName,
}: PlayerStatisticsProps) {
    return (
        <div
            className="rounded-lg p-6 shadow-[4px_6px_0px_rgba(0,0,0)] border-4 border-black"
            style={{ minHeight: "400px", backgroundColor: "var(--scroll-tan)" }}
        >
            <h3 className="text-2xl font-bold mb-4 flex items-center gap-2">
                Student Statistics
            </h3>
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
                {players.map((player, index) => (
                    <PlayerCard
                        key={index}
                        playerIndex={index}
                        studentName={getStudentName(index)}
                        currentWords={player.words.length}
                        stats={playerStats.get(index)}
                    />
                ))}
                {players.length === 0 && (
                    <div
                        className="text-center py-8 font-semibold"
                        style={{ color: "var(--ocean-dark)" }}
                    >
                        No students playing yet
                    </div>
                )}
            </div>
        </div>
    );
}
