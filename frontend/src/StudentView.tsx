import BeachTile from "./components/BeachTile";
import WordTile from "./components/WordTile";
import WavePattern from "./components/WavePattern";
import ScrollHint from "./components/ScrollHint";

interface StudentViewProps {
    availableLetters?: string[];
    playerWords?: string[];
    opponentWords?: string[];
    hint?: string;
}

export default function StudentView({
    availableLetters = ["A", "B", "C", "O", "E"],
    playerWords = ["CAT", "BOAT"],
    opponentWords = ["DOG", "FISH"],
    hint = "Hint #1: There is a three letter word available",
}: StudentViewProps) {
    return (
        <div className="min-h-screen flex flex-col items-center justify-start py-12 px-8">
            <header className="mb-12">
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
                <div className="flex gap-4 justify-center">
                    {availableLetters.map((letter, i) => (
                        <BeachTile key={i} letter={letter} size="small" />
                    ))}
                </div>
            </section>

            <section className="mb-4">
                <div className="flex gap-6 justify-center flex-wrap">
                    {playerWords.map((word, i) => (
                        <WordTile
                            key={i}
                            word={word}
                            backgroundColor="var(--sand-yellow)"
                            borderColor="#d4b55c"
                        />
                    ))}
                </div>
            </section>

            <WavePattern count={5} />

            <section className="mb-8 mt-4">
                <div className="flex gap-6 justify-center flex-wrap">
                    {opponentWords.map((word, i) => (
                        <WordTile
                            key={i}
                            word={word}
                            backgroundColor="var(--sand-yellow)"
                            borderColor={i === 0 ? "#c44e4e" : "#4e7bc4"}
                        />
                    ))}
                </div>
            </section>

            <section className="mt-8">
                <ScrollHint hint={hint} width={600} />
            </section>
        </div>
    );
}
