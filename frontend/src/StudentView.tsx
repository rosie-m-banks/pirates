import { useEffect, useState, useMemo } from "react";

import BeachTile from "./components/BeachTile";
import WordTile from "./components/WordTile";
import WavePattern from "./components/WavePattern";
import ScrollHint from "./components/ScrollHint";
import { fetchDefinition } from "./utils/definition";

import type { GameData } from "./App";

// Color palette for different players (beach/pirate themed)
export const PLAYER_COLORS = [
    { bg: "#e8b86d", border: "#d4a355", label: "Captain" }, // Gold
    { bg: "#6b9ac4", border: "#4e7ba8", label: "First Mate" }, // Ocean Blue
    { bg: "#c96b6b", border: "#b35454", label: "Quartermaster" }, // Coral Red
    { bg: "#7bc47b", border: "#5fa85f", label: "Navigator" }, // Sea Green
    { bg: "#b584c4", border: "#9966a8", label: "Gunner" }, // Purple
    { bg: "#c4a76b", border: "#a8895f", label: "Cook" }, // Sandy Brown
];

export default function StudentView({
    availableLetters = "abced",
    players = [
        { words: ["CAT", "BOAT", "HELLO"] },
        { words: ["SHIP", "ANCHOR", "TREASURE"] },
        { words: ["PARROT", "MAP", "GOLD"] },
    ],
    recommendedWords = {},
}: GameData) {
    const [numHints, setNumHints] = useState(0);
    const [targetWordDefinition, setTargetWordDefinition] = useState<string | null>(null);

    const letterList = availableLetters.toUpperCase().split("");

    // Get the first recommended word and its construction
    const targetWord = useMemo(() => {
        const words = Object.keys(recommendedWords);
        return words.length > 0 ? words[0] : null;
    }, [recommendedWords]);

    // Reset hints and definition when target word changes
    useEffect(() => {
        setNumHints(0);
        setTargetWordDefinition(null);
    }, [targetWord]);

    // Fetch definition when second hint is requested
    useEffect(() => {
        if (targetWord && numHints >= 1 && !targetWordDefinition) {
            fetchDefinition(targetWord).then((definition) => {
                setTargetWordDefinition(definition);
            });
        }
    }, [targetWord, numHints, targetWordDefinition]);

    const construction = targetWord ? recommendedWords[targetWord] : [];

    // Analyze what type of construction this is
    const constructionType = useMemo(() => {
        if (!targetWord || construction.length === 0 || players.length === 0)
            return null;

        const selfWords = players[0].words;
        const otherPlayerWords = players.slice(1).flatMap((p) => p.words);
        const usesOpponentWord = construction.some((part) =>
            otherPlayerWords.some(
                (w) => w.toLowerCase() === part.toLowerCase(),
            ),
        );
        const usesSelfWord = construction.some((part) =>
            selfWords.some((w) => w.toLowerCase() === part.toLowerCase()),
        );

        const usesAvailableLetters = construction.some(
            (part) =>
                part.length === 1 &&
                availableLetters.toLowerCase().includes(part.toLowerCase()),
        );

        if (usesSelfWord && usesOpponentWord) return "combine";
        if (usesSelfWord) return "add-to-word";
        if (usesOpponentWord) return "steal";
        if (usesAvailableLetters) return "make-from-center";
    }, [targetWord, construction, players, availableLetters]);

    // Generate individual hint text for a specific level
    const getHintText = (level: number): string => {
        if (!targetWord) {
            return "No words available...";
        }

        switch (level) {
            case 0:
                // hint 1: General guidance based on construction type
                if (constructionType === "add-to-word") {
                    return "You can add letters to one of your existing words!";
                } else if (constructionType === "steal") {
                    return "You can combine words from different players!";
                } else if (constructionType === "make-from-center") {
                    return "You can make a new word from the available letters!";
                } else {
                    return "You can combine your word and an opponent's word!";
                }

            case 1: {
                // hint 2: Tell them which word can be changed
                const sourceWord = construction.find((part) =>
                    players
                        .flatMap((p) => p.words)
                        .some((w) => w.toLowerCase() === part.toLowerCase()),
                );
                if (sourceWord) {
                    return `Try using the word "${sourceWord.toUpperCase()}"`;
                }
                return `Try combining: ${construction
                    .map((p) => p.toUpperCase())
                    .sort()
                    .join(", ")}`;
            }
            case 2:
                // hint 3. Tell them the definition of the word
                if (targetWordDefinition) {
                    return `The definition of the word you can make is: ${targetWordDefinition}`;
                }
            case 3:
                // hint 4: Tell them the length of the final word
                return `The word you can make is ${targetWord.length} letters long`;

            case 4: {
                // hint 5: Hangman style - show first and last letter, hide middle
                const upper = targetWord.toUpperCase();
                const hangman =
                    upper[0] +
                    "_".repeat(upper.length - 2) +
                    upper[upper.length - 1];
                return `The word looks like: ${hangman}`;
            }

            default:
                // Reveal the answer
                return `The word is "${targetWord.toUpperCase()}" = ${construction.map((p) => p.toUpperCase()).join(" + ")}`;
        }
    };

    // Generate array of all hints shown so far
    const allHints = useMemo(() => {
        const hints: string[] = [];
        for (let i = 0; i <= numHints; i++) {
            hints.push(getHintText(i));
        }
        return hints;
    }, [numHints, targetWord, construction, constructionType, players, targetWordDefinition]);

    // Function to advance to next hint
    function getNextHint() {
        setNumHints((prev) => prev + 1);
    }

    return (
        <div>
            <section className="mb-8 flex flex-col items-center gap-4 w-full">
                {/* Display all hints accumulated so far */}
                <div className="flex flex-col gap-3 w-full">
                    <ScrollHint hints={allHints} />
                </div>

                {/* Button to get next hint */}
                {targetWord && numHints < 4 && (
                    <button
                        onClick={getNextHint}
                        className="px-6 py-3 rounded-lg font-bold shadow-[4px_6px_0px_rgba(0,0,0)] hover:scale-105 transition-transform"
                        style={{
                            backgroundColor: "#6b9ac4",
                            color: "white",
                            border: "3px solid #4e7ba8",
                            fontSize: "1rem",
                        }}
                    >
                        Need Another Hint?
                    </button>
                )}
            </section>

            <section className="mb-8">
                <div className="flex gap-4 justify-center">
                    {letterList.map((letter, i) => (
                        <BeachTile key={i} letter={letter} size="small" />
                    ))}
                </div>
            </section>

            <WavePattern count={3}></WavePattern>

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
