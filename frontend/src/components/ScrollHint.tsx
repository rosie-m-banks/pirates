interface ScrollHintProps {
    hints: string[];
    width?: number;
}

export default function ScrollHint({ hints, width = 600 }: ScrollHintProps) {
    const rollWidth = 40;

    // Estimate height based on text length and width
    // Silkscreen at text-sm (~14px) is ~10px per char; px-12 = 96px horizontal padding
    const charsPerLine = Math.floor((width - 96) / 10);
    const estimatedLines = hints.reduce(
        (total, hint) =>
            total + Math.max(1, Math.ceil(hint.length / charsPerLine)),
        0,
    );
    const lineHeight = 24; // leading-relaxed with text-sm
    const gapHeight = (hints.length - 1) * 8; // gap-2 between hints
    const verticalPadding = 60; // Top and bottom padding combined
    const height = estimatedLines * lineHeight + gapHeight + verticalPadding;

    return (
        <div className="relative inline-block w-full">
            <svg
                className="w-full"
                style={{ height: `${height}px` }}
                viewBox={`0 0 ${width} ${height}`}
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                preserveAspectRatio="none"
            >
                <defs>
                    <pattern
                        id="paperTexture"
                        x="0"
                        y="0"
                        width="4"
                        height="4"
                        patternUnits="userSpaceOnUse"
                    >
                        <rect width="4" height="4" fill="var(--scroll-tan)" />
                        <circle
                            cx="1"
                            cy="1"
                            r="0.5"
                            fill="var(--scroll-dark)"
                            opacity="0.1"
                        />
                        <circle
                            cx="3"
                            cy="3"
                            r="0.5"
                            fill="var(--scroll-dark)"
                            opacity="0.1"
                        />
                    </pattern>
                </defs>

                <rect
                    x={3}
                    y="20"
                    width={width - 6}
                    height={height - 40}
                    fill="url(#paperTexture)"
                    stroke="#000"
                    strokeWidth="2"
                />

                <path
                    d={`M ${10} 30 L ${10} ${height - 30}`}
                    stroke="var(--scroll-dark)"
                    strokeWidth="1"
                    opacity="0.3"
                />
                <path
                    d={`M ${width - 10} 30 L ${width - 10} ${height - 30}`}
                    stroke="var(--scroll-dark)"
                    strokeWidth="1"
                    opacity="0.3"
                />
            </svg>

            <div
                className="absolute inset-0 flex items-center justify-center text-center px-12 py-5"
                style={{ fontFamily: "Silkscreen, monospace" }}
            >
                <div className="flex flex-col gap-2">
                    {hints.map((hint, index) => (
                        <p
                            className={`text-sm leading-relaxed max-w-full ${index !== hints.length - 1 ? "text-black/50" : "text-black"}`}
                        >
                            {hint}
                        </p>
                    ))}
                </div>
            </div>
        </div>
    );
}
