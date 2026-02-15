import MoveLogEntry from "./MoveLogEntry";
import type { MoveLogEntry as MoveLogEntryType } from "../hooks/useMoveLog";

interface MoveLogProps {
    entries: MoveLogEntryType[];
    isLoading?: boolean;
    error?: string | null;
}

/**
 * Move log container displaying all student word plays
 */
export default function MoveLog({ entries, isLoading, error }: MoveLogProps) {
    return (
        <div className="shrink relative">
            <div className="space-y-2 max-h-[600px] overflow-y-auto no-scrollbar">
                {isLoading && (
                    <div className="text-center text-gray-500 py-8">
                        Loading move log...
                    </div>
                )}
                {error && (
                    <div className="text-center text-red-500 py-8">
                        Error: {error}
                    </div>
                )}
                {!isLoading && !error && entries.length === 0 && (
                    <div className="text-center text-gray-500 py-8">
                        No moves logged yet. Waiting for students to play...
                    </div>
                )}
                {!isLoading &&
                    !error &&
                    entries.map((entry) => (
                        <MoveLogEntry
                            key={entry.id}
                            timestamp={entry.timestamp}
                            playerIndex={entry.playerIndex}
                            studentName={entry.studentName}
                            word={entry.word}
                            frequencyScore={entry.frequencyScore}
                        />
                    ))}
            </div>
            <div
                className="absolute bottom-0 left-0 right-0 h-16 pointer-events-none"
                style={{
                    background:
                        "linear-gradient(to bottom, transparent, var(--ocean-blue))",
                }}
            />
        </div>
    );
}
