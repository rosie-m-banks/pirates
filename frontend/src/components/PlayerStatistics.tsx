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
        <div>
            <div className="pb-3 font-bold text-[var(--wave-color)]">
                Students:{" "}
            </div>
            <div className="flex flex-row gap-3">
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
