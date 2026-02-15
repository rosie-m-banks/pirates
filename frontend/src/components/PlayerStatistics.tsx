import PlayerCard from "./PlayerCard";

interface Player {
    words: string[];
}

interface PlayerStats {
    playerId: string;
    totalWords: number;
    uniqueWords: number;
    vocabularyDiversity: number;
    avgWordFrequency: number;
    vocabularyLevel: string;
}

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
            className="bg-white rounded-xl p-6 shadow-lg border-4 border-black"
            style={{ minHeight: "400px" }}
        >
            <h3 className="text-2xl font-bold mb-4 flex items-center gap-2">
                📊 Student Statistics
            </h3>
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
                {players.map((player, index) => (
                    <PlayerCard
                        key={index}
                        studentName={getStudentName(index)}
                        currentWords={player.words.length}
                        stats={playerStats.get(index)}
                    />
                ))}
                {players.length === 0 && (
                    <div className="text-center text-gray-500 py-8">
                        No students playing yet
                    </div>
                )}
            </div>
        </div>
    );
}
