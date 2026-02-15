interface ScrollHintProps {
  hint: string;
  width?: number;
}

export default function ScrollHint({ hint, width = 600 }: ScrollHintProps) {
  const height = 120;
  const rollWidth = 40;

  return (
    <div className="relative inline-block" style={{ width: width + rollWidth * 2 }}>
      <svg
        className="w-full h-full"
        viewBox={`0 0 ${width + rollWidth * 2} ${height}`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="paperTexture" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
            <rect width="4" height="4" fill="var(--scroll-tan)" />
            <circle cx="1" cy="1" r="0.5" fill="var(--scroll-dark)" opacity="0.1" />
            <circle cx="3" cy="3" r="0.5" fill="var(--scroll-dark)" opacity="0.1" />
          </pattern>
        </defs>

        <rect
          x={rollWidth}
          y="20"
          width={width}
          height={height - 40}
          fill="url(#paperTexture)"
          stroke="#000"
          strokeWidth="2"
        />

        <ellipse
          cx={rollWidth}
          cy="20"
          rx={rollWidth - 4}
          ry="12"
          fill="var(--scroll-dark)"
          stroke="#000"
          strokeWidth="2"
        />
        <ellipse
          cx={rollWidth}
          cy="20"
          rx={rollWidth - 8}
          ry="10"
          fill="var(--scroll-tan)"
          opacity="0.5"
        />

        <ellipse
          cx={width + rollWidth}
          cy={height - 20}
          rx={rollWidth - 4}
          ry="12"
          fill="var(--scroll-dark)"
          stroke="#000"
          strokeWidth="2"
        />
        <ellipse
          cx={width + rollWidth}
          cy={height - 20}
          rx={rollWidth - 8}
          ry="10"
          fill="var(--scroll-tan)"
          opacity="0.5"
        />

        <path
          d={`M ${rollWidth + 10} 30 L ${rollWidth + 10} ${height - 30}`}
          stroke="var(--scroll-dark)"
          strokeWidth="1"
          opacity="0.3"
        />
        <path
          d={`M ${width + rollWidth - 10} 30 L ${width + rollWidth - 10} ${height - 30}`}
          stroke="var(--scroll-dark)"
          strokeWidth="1"
          opacity="0.3"
        />
      </svg>

      <div
        className="absolute inset-0 flex items-center justify-center px-20 text-center"
        style={{ fontFamily: 'Silkscreen, monospace' }}
      >
        <p className="text-sm leading-relaxed">{hint}</p>
      </div>
    </div>
  );
}
