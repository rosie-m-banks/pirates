interface WavePatternProps {
  count?: number;
}

export default function WavePattern({ count = 5 }: WavePatternProps) {
  return (
    <div className="flex gap-8 justify-center py-4">
      {Array.from({ length: count }).map((_, i) => (
        <svg
          key={i}
          width="40"
          height="16"
          viewBox="0 0 40 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="opacity-60"
        >
          <path
            d="M 0 8 Q 5 4, 10 8 Q 15 12, 20 8 Q 25 4, 30 8 Q 35 12, 40 8"
            stroke="var(--wave-color)"
            strokeWidth="2"
            fill="none"
          />
          <path
            d="M 0 12 Q 5 10, 10 12 Q 15 14, 20 12 Q 25 10, 30 12 Q 35 14, 40 12"
            stroke="var(--wave-color)"
            strokeWidth="1.5"
            fill="none"
            opacity="0.6"
          />
        </svg>
      ))}
    </div>
  );
}
