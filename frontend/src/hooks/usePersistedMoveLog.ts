import { useState, useEffect } from "react";
import { STORAGE_KEYS } from "../constants/teacher";

export interface MoveLogEntry {
    id: string;
    timestamp: number;
    studentName: string;
    word: string;
    frequencyScore: number;
}

interface UsePersistedMoveLogReturn {
    moveLog: MoveLogEntry[];
    addMoves: (entries: MoveLogEntry[]) => void;
    clearLog: () => void;
}

/**
 * Custom hook to manage persisted move log in localStorage
 */
export function usePersistedMoveLog(): UsePersistedMoveLogReturn {
    // Load persisted data from localStorage on mount
    const [moveLog, setMoveLog] = useState<MoveLogEntry[]>(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEYS.MOVE_LOG);
            return stored ? JSON.parse(stored) : [];
        } catch (error) {
            console.error("Failed to load move log from localStorage:", error);
            return [];
        }
    });

    const [seenMoveIds, setSeenMoveIds] = useState<Set<string>>(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEYS.SEEN_IDS);
            return stored ? new Set(JSON.parse(stored)) : new Set();
        } catch (error) {
            console.error("Failed to load seen IDs from localStorage:", error);
            return new Set();
        }
    });

    // Persist moveLog to localStorage whenever it changes
    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEYS.MOVE_LOG, JSON.stringify(moveLog));
        } catch (error) {
            console.error("Failed to save move log to localStorage:", error);
        }
    }, [moveLog]);

    // Persist seenMoveIds to localStorage whenever it changes
    useEffect(() => {
        try {
            localStorage.setItem(
                STORAGE_KEYS.SEEN_IDS,
                JSON.stringify(Array.from(seenMoveIds))
            );
        } catch (error) {
            console.error("Failed to save seen IDs to localStorage:", error);
        }
    }, [seenMoveIds]);

    /**
     * Add new moves to the log (deduplicates automatically)
     */
    const addMoves = (entries: MoveLogEntry[]) => {
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
    };

    /**
     * Clear the entire move log
     */
    const clearLog = () => {
        if (
            confirm(
                "Are you sure you want to clear the move log? This cannot be undone."
            )
        ) {
            setMoveLog([]);
            setSeenMoveIds(new Set());
            localStorage.removeItem(STORAGE_KEYS.MOVE_LOG);
            localStorage.removeItem(STORAGE_KEYS.SEEN_IDS);
        }
    };

    return {
        moveLog,
        addMoves,
        clearLog,
    };
}
