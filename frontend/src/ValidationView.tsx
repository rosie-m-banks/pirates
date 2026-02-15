import { useMemo, useState } from "react";

import type { GameData } from "./App";

// Construction type labels
const CONSTRUCTION_TYPE_LABELS: Record<string, string> = {
    steal: "Steal",
    "add-to-word": "Add to Word",
    combine: "Combine",
    "make-from-center": "Make from Center",
};

type SortField = "word" | "type" | "length";

interface WordConstruction {
    word: string;
    construction: string[];
    type: string | null;
    backendRank: number; // Original ranking from backend (1-indexed)
}

// Extract construction analysis logic
function analyzeConstruction(
    targetWord: string,
    construction: string[],
    players: { words: string[] }[],
    availableLetters: string,
): string | null {
    if (construction.length === 0 || players.length === 0) return null;

    const selfWords = players[0].words;
    const otherPlayerWords = players.slice(1).flatMap((p) => p.words);

    const usesOpponentWord = construction.some((part) =>
        otherPlayerWords.some((w) => w.toLowerCase() === part.toLowerCase()),
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
    return null;
}

export default function ValidationView({
    availableLetters = "abced",
    players = [
        { words: ["CAT", "BOAT", "HELLO"] },
        { words: ["SHIP", "ANCHOR", "TREASURE"] },
    ],
    recommendedWords = {},
}: GameData) {
    const [sortField, setSortField] = useState<SortField>("type");
    const [sortAsc, setSortAsc] = useState(true);

    // Analyze all recommended words and their constructions
    const wordConstructions = useMemo(() => {
        const words = Object.keys(recommendedWords);
        return words.map((word, index): WordConstruction => {
            const construction = recommendedWords[word];
            const type = analyzeConstruction(
                word,
                construction,
                players,
                availableLetters,
            );
            return {
                word,
                construction,
                type,
                backendRank: index + 1 // Preserve backend's original ranking
            };
        });
    }, [recommendedWords, players, availableLetters]);

    // Sort words based on selected field
    const sortedWords = useMemo(() => {
        const sorted = [...wordConstructions];
        sorted.sort((a, b) => {
            let comparison = 0;
            switch (sortField) {
                case "word":
                    comparison = a.word.localeCompare(b.word);
                    break;
                case "type":
                    comparison = (a.type || "unknown").localeCompare(
                        b.type || "unknown",
                    );
                    break;
                case "length":
                    comparison = a.word.length - b.word.length;
                    break;
            }
            return sortAsc ? comparison : -comparison;
        });
        return sorted;
    }, [wordConstructions, sortField, sortAsc]);

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortAsc(!sortAsc);
        } else {
            setSortField(field);
            setSortAsc(true);
        }
    };

    return (
        <div className="w-full max-w-7xl">
            {/* Summary Section */}
            <div className="mb-6 p-4 bg-gray-100 rounded border-2 border-gray-300">
                <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                        <div className="text-sm text-gray-600">Total Words</div>
                        <div className="text-2xl font-bold">
                            {wordConstructions.length}
                        </div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-600">
                            Available Letters
                        </div>
                        <div className="text-xl font-bold">
                            {availableLetters.toUpperCase()}
                        </div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-600">Players</div>
                        <div className="text-2xl font-bold">
                            {players.length}
                        </div>
                    </div>
                </div>
            </div>

            {/* Player Words Summary */}
            <div className="mb-6 p-4 bg-blue-50 rounded border-2 border-blue-300">
                <div className="text-sm font-bold mb-2">
                    Current Game State:
                </div>
                {players.map((player, idx) => (
                    <div key={idx} className="text-sm mb-1">
                        <span className="font-semibold">Player {idx + 1}:</span>{" "}
                        {player.words.join(", ")}
                    </div>
                ))}
            </div>

            {/* Words Table */}
            {wordConstructions.length === 0 ? (
                <div className="text-center text-gray-500 text-lg p-8">
                    No recommended words yet...
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full border-collapse border-2 border-gray-300">
                        <thead>
                            <tr className="bg-gray-200">
                                <th className="border border-gray-300 px-4 py-2 text-left" title="Ranking from backend scoring system">
                                    Rank
                                </th>
                                <th
                                    className="border border-gray-300 px-4 py-2 text-left cursor-pointer hover:bg-gray-300"
                                    onClick={() => handleSort("word")}
                                >
                                    Word{" "}
                                    {sortField === "word" &&
                                        (sortAsc ? "↑" : "↓")}
                                </th>
                                <th
                                    className="border border-gray-300 px-4 py-2 text-left cursor-pointer hover:bg-gray-300"
                                    onClick={() => handleSort("length")}
                                >
                                    Length{" "}
                                    {sortField === "length" &&
                                        (sortAsc ? "↑" : "↓")}
                                </th>
                                <th className="border border-gray-300 px-4 py-2 text-left">
                                    Construction
                                </th>
                                <th
                                    className="border border-gray-300 px-4 py-2 text-left cursor-pointer hover:bg-gray-300"
                                    onClick={() => handleSort("type")}
                                >
                                    Type{" "}
                                    {sortField === "type" &&
                                        (sortAsc ? "↑" : "↓")}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedWords.map(
                                ({ word, construction, type, backendRank }, idx) => (
                                    <tr
                                        key={idx}
                                        className="hover:bg-gray-50 even:bg-gray-100"
                                    >
                                        <td className="border border-gray-300 px-4 py-2 text-gray-600 font-semibold">
                                            {backendRank}
                                        </td>
                                        <td className="border border-gray-300 px-4 py-2 font-bold text-lg">
                                            {word.toUpperCase()}
                                        </td>
                                        <td className="border border-gray-300 px-4 py-2 text-center">
                                            {word.length}
                                        </td>
                                        <td className="border border-gray-300 px-4 py-2 font-mono text-sm">
                                            {construction
                                                .map((p) => p.toUpperCase())
                                                .join(" + ")}
                                        </td>
                                        <td className="border border-gray-300 px-4 py-2">
                                            <span
                                                className="px-2 py-1 rounded text-sm font-semibold"
                                                style={{
                                                    backgroundColor:
                                                        type === "steal"
                                                            ? "#fecaca"
                                                            : type === "combine"
                                                              ? "#fde68a"
                                                              : type ===
                                                                  "add-to-word"
                                                                ? "#bfdbfe"
                                                                : "#bbf7d0",
                                                    color: "#1f2937",
                                                }}
                                            >
                                                {CONSTRUCTION_TYPE_LABELS[
                                                    type || "unknown"
                                                ] || "Unknown"}
                                            </span>
                                        </td>
                                    </tr>
                                ),
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
