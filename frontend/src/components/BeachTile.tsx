interface BeachTileProps {
  letter: string;
  size?: 'small' | 'large';
}

export default function BeachTile({ letter, size = 'small' }: BeachTileProps) {
  const dimensions = size === 'small' ? 'w-16 h-16' : 'w-20 h-20';
  const textSize = size === 'small' ? 'text-3xl' : 'text-4xl';

  return (
    <div
      className={`${dimensions} relative inline-block`}
      style={{
        transform: `rotate(${Math.random() * 6 - 3}deg)`,
      }}
    >
      <svg
        className="absolute inset-0 w-full h-full"
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M 2 8 L 8 2 L 56 2 L 62 8 L 62 56 L 56 62 L 8 62 L 2 56 Z"
          fill="var(--sand-yellow)"
          stroke="#000"
          strokeWidth="2"
        />
        <path
          d="M 4 10 L 10 4 L 54 4 L 60 10 L 60 54 L 54 60 L 10 60 L 4 54 Z"
          fill="none"
          stroke="var(--sand-dark)"
          strokeWidth="1"
          opacity="0.5"
        />
        <path d="M 10 6 L 12 6" stroke="#000" strokeWidth="2" />
        <path d="M 18 4 L 20 4" stroke="#000" strokeWidth="2" />
        <path d="M 52 6 L 54 6" stroke="#000" strokeWidth="2" />
        <path d="M 60 14 L 60 16" stroke="#000" strokeWidth="2" />
        <path d="M 60 48 L 60 50" stroke="#000" strokeWidth="2" />
        <path d="M 6 56 L 6 58" stroke="#000" strokeWidth="2" />
      </svg>
      <div
        className={`absolute inset-0 flex items-center justify-center ${textSize} font-bold uppercase`}
      >
        {letter}
      </div>
    </div>
  );
}
