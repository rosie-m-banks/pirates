/**
 * Type definitions for Teacher View
 */

import type { GameData } from "../App";

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
    _analytics?: AnalyticsData;
}
