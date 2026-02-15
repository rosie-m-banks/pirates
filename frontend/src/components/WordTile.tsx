import { useState, useEffect } from "react";
import { fetchDefinition } from "../utils/definition";

interface WordTileProps {
    word: string;
    borderColor?: string;
    backgroundColor?: string;
}

export default function WordTile({
    word,
    borderColor = "#8b4513",
    backgroundColor = "var(--sand-yellow)",
}: WordTileProps) {
    const letters = word.toUpperCase().split("");
    const width = letters.length * 48 + 32;
    const [isHovered, setIsHovered] = useState(false);
    const [definition, setDefinition] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    // Fetch definition when hovered
    useEffect(() => {
        if (isHovered && !definition && !isLoading) {
            setIsLoading(true);
            fetchDefinition(word).then((def) => {
                setDefinition(def);
                setIsLoading(false);
            });
        }
    }, [isHovered, word, definition, isLoading]);

    return (
        <div
            className="relative inline-block"
            style={{
                transform: `rotate(${Math.random() * 4 - 2}deg)`,
            }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <svg
                className="absolute inset-0 w-full h-full"
                viewBox={`0 0 ${width} 80`}
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                style={{
                    WebkitFilter: "drop-shadow( 3px 3px 0px rgba(0, 0, 0))",
                    filter: "drop-shadow( 3px 3px 0px rgba(0, 0, 0, 1))",
                }}
            >
                <path
                    d={`M 4 12 L 12 4 L ${width - 12} 4 L ${width - 4} 12 L ${width - 4} 68 L ${width - 12} 76 L 12 76 L 4 68 Z`}
                    fill={backgroundColor}
                    stroke="#000"
                    strokeWidth="2"
                />
                <path
                    d={`M 6 14 L 14 6 L ${width - 14} 6 L ${width - 6} 14 L ${width - 6} 66 L ${width - 14} 74 L 14 74 L 6 66 Z`}
                    fill="none"
                    stroke={borderColor}
                    strokeWidth="3"
                    opacity="0.4"
                />
                <path d="M 16 8 L 18 8" stroke="#000" strokeWidth="2" />
                <path
                    d={`M ${width - 22} 8 L ${width - 20} 8`}
                    stroke="#000"
                    strokeWidth="2"
                />
                <path d="M 8 20 L 8 22" stroke="#000" strokeWidth="2" />
                <path d="M 8 56 L 8 58" stroke="#000" strokeWidth="2" />
            </svg>
            <div className="relative flex items-center justify-center h-20 px-4 gap-1">
                {letters.map((letter, i) => (
                    <span key={i}>
                        <span className="text-3xl font-bold">{letter}</span>
                        {i < letters.length - 1 && (
                            <span className="text-2xl opacity-50 mx-1">:</span>
                        )}
                    </span>
                ))}
            </div>

            {/* Tooltip */}
            {isHovered && (
                <div
                    className="absolute z-50 bg-white border-2 border-gray-800 rounded-lg shadow-lg p-3 max-w-xs pointer-events-none"
                    style={{
                        bottom: "100%",
                        left: "50%",
                        transform: "translateX(-50%) translateY(-8px)",
                        marginBottom: "8px",
                    }}
                >
                    <div className="text-sm font-semibold mb-1 text-gray-800">
                        {word.toUpperCase()}
                    </div>
                    {isLoading ? (
                        <div className="text-xs text-gray-600">Loading definition...</div>
                    ) : definition ? (
                        <div className="text-xs text-gray-700">{definition}</div>
                    ) : (
                        <div className="text-xs text-gray-500">Definition not available</div>
                    )}
                    {/* Tooltip arrow */}
                    <div
                        className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1"
                        style={{
                            width: 0,
                            height: 0,
                            borderLeft: "8px solid transparent",
                            borderRight: "8px solid transparent",
                            borderTop: "8px solid white",
                        }}
                    />
                    <div
                        className="absolute top-full left-1/2 transform -translate-x-1/2"
                        style={{
                            width: 0,
                            height: 0,
                            borderLeft: "9px solid transparent",
                            borderRight: "9px solid transparent",
                            borderTop: "9px solid #1f2937",
                            marginTop: "-1px",
                        }}
                    />
                </div>
            )}
        </div>
    );
}
