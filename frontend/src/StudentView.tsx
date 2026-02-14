import BeachTile from "./components/BeachTile";
import WordTile from "./components/WordTile";
import WavePattern from "./components/WavePattern";
import ScrollHint from "./components/ScrollHint";

interface Player {
    words: string[];
}

interface StudentViewProps {
    availableLetters?: string[];
    players?: Player[];
    hint?: string;
}

// Color palette for different players (beach/pirate themed)
const PLAYER_COLORS = [
    { bg: "#e8b86d", border: "#d4a355", label: "Captain" }, // Gold
    { bg: "#6b9ac4", border: "#4e7ba8", label: "First Mate" }, // Ocean Blue
    { bg: "#c96b6b", border: "#b35454", label: "Quartermaster" }, // Coral Red
    { bg: "#7bc47b", border: "#5fa85f", label: "Navigator" }, // Sea Green
    { bg: "#b584c4", border: "#9966a8", label: "Gunner" }, // Purple
    { bg: "#c4a76b", border: "#a8895f", label: "Cook" }, // Sandy Brown
];

export default function StudentView({
    availableLetters = ["A", "B", "C", "D", "E"],
    players = [
        { words: ["CAT", "BOAT", "HELLO"] },
        { words: ["SHIP", "ANCHOR", "TREASURE"] },
        { words: ["PARROT", "MAP", "GOLD"] },
    ],
    hint = "Hint #1: There is a three letter word available",
}: StudentViewProps) {
    return (
        <div className="min-h-screen flex flex-col items-center justify-start py-12 px-8">
            <header className="mb-8">
                <h1
                    className="relative text-8xl tracking-wider flex items-center gap-4"
                    style={{
                        fontFamily: "FatPix, sans-serif",
                    }}
                >
                    {/* Shadow layer */}
                    <span className="absolute top-2 left-2 text-black/60 select-none pointer-events-none">
                        Pirates
                    </span>

                    {/* Main text */}
                    <span
                        className="relative text-(--ocean-blue)"
                        style={{ WebkitTextStroke: "4px white" }}
                    >
                        Pirates
                    </span>
                </h1>
            </header>

            <section className="mb-8">
                <ScrollHint hint={hint} width={600} />
            </section>

            <section className="">
                <div className=""></div>
            </section>

            <section className="mb-8">
                <div className="flex gap-4 justify-center">
                    {availableLetters.map((letter, i) => (
                        <BeachTile key={i} letter={letter} size="small" />
                    ))}
                </div>
            </section>

            {players.map((player, playerIndex) => {
                const colorScheme =
                    PLAYER_COLORS[playerIndex % PLAYER_COLORS.length];

                return (
                    <div key={playerIndex} className="w-full mb-8">
                        <div className="flex flex-col items-center">
                            <div className="flex gap-6 justify-center flex-wrap max-w-5xl">
                                {player.words.map((word, wordIndex) => (
                                    <WordTile
                                        key={wordIndex}
                                        word={word}
                                        borderColor={colorScheme.border}
                                    />
                                ))}
                            </div>
                        </div>

                        {/* Wave separator between players (except after last player) */}
                        {playerIndex == 0 && (
                            <div className="mt-8">
                                <WavePattern count={3} />
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
