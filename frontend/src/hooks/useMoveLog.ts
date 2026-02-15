import { useState, useEffect, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import { getStudentName } from "../TeacherView";

export interface MoveLogEntry {
    id: string;
    timestamp: number;
    playerIndex: number;
    studentName: string;
    word: string;
    frequencyScore: number;
}

interface BackendLogEvent {
    id: string; // Backend now provides this
    sessionId: string;
    timestamp: number;
    eventType: string;
    playerId: string;
    playerIndex: number;
    word: string;
    frequencyScore: number;
    metadata: {
        playerIndex: number;
    };
}

interface UseMoveLogReturn {
    moveLog: MoveLogEntry[];
    addMoves: (entries: MoveLogEntry[]) => void;
    isLoading: boolean;
    error: string | null;
}

/**
 * Custom hook to manage move log from backend + real-time updates
 */
export function useMoveLog(): UseMoveLogReturn {
    const [moveLog, setMoveLog] = useState<MoveLogEntry[]>([]);
    const [seenMoveIds, setSeenMoveIds] = useState<Set<string>>(new Set());
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch full log from backend on mount
    useEffect(() => {
        const fetchLog = async () => {
            try {
                setIsLoading(true);
                const response = await fetch(
                    "http://localhost:3000/analytics/move-log",
                );
                const data = await response.json();

                if (data.ok && data.data.events) {
                    const entries: MoveLogEntry[] = data.data.events
                        .reverse()
                        .map((event: BackendLogEvent) => {
                            const playerIndex =
                                event.metadata?.playerIndex ??
                                event.playerIndex ??
                                0;
                            return {
                                id: event.id,
                                timestamp: event.timestamp,
                                playerIndex,
                                studentName: getStudentName(playerIndex),
                                word: event.word,
                                frequencyScore: event.frequencyScore,
                            };
                        });

                    setMoveLog(entries);
                    setSeenMoveIds(new Set(entries.map((e) => e.id)));
                }
            } catch (err) {
                console.error("Failed to fetch move log:", err);
                setError("Failed to load move log from server");
            } finally {
                setIsLoading(false);
            }
        };

        fetchLog();
    }, []);

    /**
     * Add new moves to the log (deduplicates automatically)
     */
    const addMoves = useCallback(
        (entries: MoveLogEntry[]) => {
            const newEntries: MoveLogEntry[] = [];
            const newIds: string[] = [];

            entries.forEach((entry) => {
                if (!seenMoveIds.has(entry.id)) {
                    newEntries.push(entry);
                    newIds.push(entry.id);
                }
            });

            if (newEntries.length > 0) {
                setMoveLog((prev) => [...newEntries, ...prev]);
                setSeenMoveIds((prev) => {
                    const updated = new Set(prev);
                    newIds.forEach((id) => updated.add(id));
                    return updated;
                });
            }
        },
        [seenMoveIds],
    );

    // Listen to dedicated move-log WebSocket event for real-time updates
    useEffect(() => {
        const socket: Socket = io("http://localhost:3000", {
            path: "/receive-data",
        });

        socket.on("connect", () => {
            console.log("Connected to move-log WebSocket");
        });

        socket.on("move-log", (data: { entries: BackendLogEvent[] }) => {
            if (data.entries && data.entries.length > 0) {
                const newEntries: MoveLogEntry[] = data.entries.map(
                    (event: BackendLogEvent) => {
                        const playerIndex =
                            event.metadata?.playerIndex ??
                            event.playerIndex ??
                            0;
                        return {
                            id: event.id,
                            timestamp: event.timestamp,
                            playerIndex,
                            studentName: getStudentName(playerIndex),
                            word: event.word,
                            frequencyScore: event.frequencyScore,
                        };
                    },
                );
                addMoves(newEntries);
            }
        });

        socket.on("disconnect", () => {
            console.log("Disconnected from move-log WebSocket");
        });

        socket.on("error", (err) => {
            console.error("WebSocket error:", err);
        });

        return () => {
            socket.disconnect();
        };
    }, [addMoves]);

    return {
        moveLog,
        addMoves,
        isLoading,
        error,
    };
}
