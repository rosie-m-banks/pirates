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

    return (
        <div
            className="relative inline-block"
            style={{
                transform: `rotate(${Math.random() * 4 - 2}deg)`,
            }}
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
        </div>
    );
}
