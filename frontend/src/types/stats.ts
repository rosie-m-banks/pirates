/**
 * Type definitions for Teacher View
 */

import type { GameData } from "../App";

export interface WordPlay {
    word: string;
    frequencyScore: number;
}

export interface MoveData {
    timestamp: number;
    players: {
        playerId: string;
        playerIndex: number;
        addedWords: WordPlay[];
        removedWords: string[];
        totalWords: number;
    }[];
}

export interface Player {
    words: string[];
}

export interface PlayerStats {
    playerId: string;
    totalWords: number;
    avgWordFrequency: number;
    vocabularyLevel: string;
}

export interface AnalyticsData {
    vocabularyStats: {
        players: PlayerStats[];
    };
}

export interface TeacherGameData extends GameData {
    move?: MoveData;
    _analytics?: AnalyticsData;
}
