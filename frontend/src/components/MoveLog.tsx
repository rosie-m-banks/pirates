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
        <div
            className="bg-white rounded-xl p-6 shadow-lg border-4 border-black"
            style={{ minHeight: "400px" }}
        >
            <div className="flex items-center gap-3 mb-4">
                <h3 className="text-2xl font-bold flex items-center gap-2">
                    📝 Move Log
                </h3>
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-semibold rounded-full">
                    {entries.length} {entries.length === 1 ? "move" : "moves"}
                </span>
            </div>

            <div className="space-y-2 max-h-[600px] overflow-y-auto">
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
                            studentName={entry.studentName}
                            word={entry.word}
                            frequencyScore={entry.frequencyScore}
                        />
                    ))}
            </div>
        </div>
    );
}
