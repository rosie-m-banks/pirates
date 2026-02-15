/**
 * State Logger: Tracks player vocabulary events for real-time analysis
 *
 * Logs when players add words to their hand, capturing:
 * - Word metadata (length, frequency, letters used)
 * - Temporal patterns (timestamps, session duration)
 * - Player progression data
 *
 * Data structure designed for easy migration to database (MongoDB, PostgreSQL, etc.)
 */

import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const LOG_DIR = join(__dirname, 'logs');
const STATE_LOG_FILE = join(LOG_DIR, 'player_vocabulary.jsonl'); // JSON Lines format for streaming
const AGGREGATE_FILE = join(LOG_DIR, 'vocabulary_aggregate.json');

// Ensure logs directory exists
if (!existsSync(LOG_DIR)) {
    mkdirSync(LOG_DIR, { recursive: true });
}

/**
 * Event types for state changes
 */
export const EventType = {
    WORD_ADDED: 'word_added',
    WORD_REMOVED: 'word_removed',
    WORD_FORMED: 'word_formed',
    SESSION_START: 'session_start',
    SESSION_END: 'session_end',
};

/**
 * In-memory aggregate data structure for real-time analysis
 * Structure designed for easy DB migration
 */
class VocabularyAggregator {
    constructor() {
        this.sessionId = Date.now().toString();
        this.sessionStart = Date.now();
        this.playerStats = new Map(); // playerId -> PlayerStats
        this.wordFrequency = new Map(); // word -> frequency count
        this.eventBuffer = []; // Recent events for batch writing
        this.bufferSize = 10;

        this.loadExistingAggregate();
    }

    /**
     * Load existing aggregate data if available
     */
    loadExistingAggregate() {
        try {
            if (existsSync(AGGREGATE_FILE)) {
                const data = JSON.parse(readFileSync(AGGREGATE_FILE, 'utf8'));
                if (data.wordFrequency) {
                    this.wordFrequency = new Map(Object.entries(data.wordFrequency));
                }
                if (data.playerStats) {
                    this.playerStats = new Map(
                        Object.entries(data.playerStats).map(([id, stats]) => [id, stats])
                    );
                }
            }
        } catch (err) {
            console.warn('Could not load existing aggregate data:', err.message);
        }
    }

    /**
     * Get or initialize player stats
     * @param {string} playerId
     */
    getPlayerStats(playerId) {
        if (!this.playerStats.has(playerId)) {
            this.playerStats.set(playerId, {
                playerId,
                totalWords: 0,
                uniqueWords: new Set(),
                wordsByLength: {},
                wordsByFrequency: {
                    common: 0,    // zipf > 5
                    medium: 0,    // zipf 3-5
                    rare: 0,      // zipf < 3
                },
                firstSeenTimestamp: Date.now(),
                lastSeenTimestamp: Date.now(),
                sessionIds: [this.sessionId],
            });
        }
        return this.playerStats.get(playerId);
    }

    /**
     * Log a vocabulary event (word added to player's hand)
     * @param {object} params
     * @param {string} params.playerId
     * @param {string} params.word
     * @param {number} params.wordLength
     * @param {number} params.frequencyScore - zipf score (0-8)
     * @param {string[]} params.lettersUsed - which letters from pool/hand were used
     * @param {string} params.eventType
     * @param {object} params.metadata - additional context
     */
    logEvent({
        playerId = 'player_0',
        word,
        wordLength,
        frequencyScore = 0,
        lettersUsed = [],
        eventType = EventType.WORD_ADDED,
        metadata = {},
    }) {
        const timestamp = Date.now();

        // Create event record
        const event = {
            sessionId: this.sessionId,
            timestamp,
            isoTimestamp: new Date(timestamp).toISOString(),
            eventType,
            playerId,
            word,
            wordLength,
            frequencyScore,
            lettersUsed,
            metadata,
        };

        // Update aggregates
        if (eventType === EventType.WORD_ADDED) {
            this.updatePlayerStats(playerId, word, wordLength, frequencyScore, timestamp);
            this.updateWordFrequency(word);
        }

        // Buffer event for batch write
        this.eventBuffer.push(event);
        if (this.eventBuffer.length >= this.bufferSize) {
            this.flushEvents();
        }

        return event;
    }

    /**
     * Update player statistics
     */
    updatePlayerStats(playerId, word, wordLength, frequencyScore, timestamp) {
        const stats = this.getPlayerStats(playerId);

        stats.totalWords++;
        stats.uniqueWords.add(word);
        stats.lastSeenTimestamp = timestamp;

        // Track word length distribution
        if (!stats.wordsByLength[wordLength]) {
            stats.wordsByLength[wordLength] = 0;
        }
        stats.wordsByLength[wordLength]++;

        // Track frequency distribution
        if (frequencyScore > 5) {
            stats.wordsByFrequency.common++;
        } else if (frequencyScore >= 3) {
            stats.wordsByFrequency.medium++;
        } else {
            stats.wordsByFrequency.rare++;
        }
    }

    /**
     * Update word frequency counts
     */
    updateWordFrequency(word) {
        const count = this.wordFrequency.get(word) || 0;
        this.wordFrequency.set(word, count + 1);
    }

    /**
     * Flush event buffer to disk (JSONL format for streaming)
     */
    flushEvents() {
        if (this.eventBuffer.length === 0) return;

        try {
            const lines = this.eventBuffer.map(event => JSON.stringify(event)).join('\n') + '\n';
            writeFileSync(STATE_LOG_FILE, lines, { flag: 'a' });
            this.eventBuffer = [];
        } catch (err) {
            console.error('Failed to write events to log:', err);
        }
    }

    /**
     * Save aggregate statistics to disk
     */
    saveAggregate() {
        this.flushEvents(); // Ensure all events are written

        const aggregate = {
            sessionId: this.sessionId,
            sessionStart: this.sessionStart,
            lastUpdate: Date.now(),
            playerStats: Object.fromEntries(
                Array.from(this.playerStats.entries()).map(([id, stats]) => [
                    id,
                    {
                        ...stats,
                        uniqueWords: Array.from(stats.uniqueWords),
                    },
                ])
            ),
            wordFrequency: Object.fromEntries(this.wordFrequency),
            totalEvents: this.getTotalEvents(),
        };

        try {
            writeFileSync(AGGREGATE_FILE, JSON.stringify(aggregate, null, 2));
        } catch (err) {
            console.error('Failed to write aggregate data:', err);
        }
    }

    /**
     * Get current vocabulary statistics for a player
     * @param {string} playerId
     */
    getPlayerVocabularyStats(playerId) {
        const stats = this.getPlayerStats(playerId);
        return {
            playerId: stats.playerId,
            totalWords: stats.totalWords,
            uniqueWordsCount: stats.uniqueWords.size,
            vocabularyDiversity: stats.uniqueWords.size / Math.max(1, stats.totalWords),
            wordsByLength: stats.wordsByLength,
            wordsByFrequency: stats.wordsByFrequency,
            avgWordLength: this.calculateAvgWordLength(stats.wordsByLength),
            sessionDuration: Date.now() - stats.firstSeenTimestamp,
        };
    }

    /**
     * Calculate average word length for a player
     */
    calculateAvgWordLength(wordsByLength) {
        let totalLength = 0;
        let totalWords = 0;
        for (const [length, count] of Object.entries(wordsByLength)) {
            totalLength += parseInt(length) * count;
            totalWords += count;
        }
        return totalWords > 0 ? totalLength / totalWords : 0;
    }

    /**
     * Get total number of logged events
     */
    getTotalEvents() {
        try {
            if (existsSync(STATE_LOG_FILE)) {
                const content = readFileSync(STATE_LOG_FILE, 'utf8');
                return content.split('\n').filter(line => line.trim()).length;
            }
        } catch (err) {
            console.error('Error counting events:', err);
        }
        return 0;
    }

    /**
     * Get real-time analytics snapshot
     */
    getRealTimeAnalytics() {
        const players = Array.from(this.playerStats.values()).map(stats => ({
            playerId: stats.playerId,
            totalWords: stats.totalWords,
            uniqueWords: stats.uniqueWords.size,
            vocabularyDiversity: stats.uniqueWords.size / Math.max(1, stats.totalWords),
            avgWordLength: this.calculateAvgWordLength(stats.wordsByLength),
        }));

        return {
            sessionId: this.sessionId,
            sessionDuration: Date.now() - this.sessionStart,
            totalPlayers: this.playerStats.size,
            players,
            topWords: this.getTopWords(10),
            totalUniqueWords: this.wordFrequency.size,
        };
    }

    /**
     * Get most frequently used words
     */
    getTopWords(limit = 10) {
        return Array.from(this.wordFrequency.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit)
            .map(([word, count]) => ({ word, count }));
    }
}

// Singleton instance
let aggregatorInstance = null;

/**
 * Get or create the vocabulary aggregator instance
 */
export function getAggregator() {
    if (!aggregatorInstance) {
        aggregatorInstance = new VocabularyAggregator();

        // Periodic save (every 30 seconds)
        setInterval(() => {
            if (aggregatorInstance) {
                aggregatorInstance.saveAggregate();
            }
        }, 30000);

        // Save on process exit
        process.on('exit', () => {
            if (aggregatorInstance) {
                aggregatorInstance.saveAggregate();
            }
        });

        process.on('SIGINT', () => {
            if (aggregatorInstance) {
                aggregatorInstance.saveAggregate();
            }
            process.exit();
        });
    }
    return aggregatorInstance;
}

/**
 * Log a state change event (convenience wrapper)
 */
export function logStateChange(params) {
    const aggregator = getAggregator();
    return aggregator.logEvent(params);
}

/**
 * Get player vocabulary statistics
 */
export function getPlayerStats(playerId) {
    const aggregator = getAggregator();
    return aggregator.getPlayerVocabularyStats(playerId);
}

/**
 * Get real-time analytics
 */
export function getRealTimeAnalytics() {
    const aggregator = getAggregator();
    return aggregator.getRealTimeAnalytics();
}

export default { getAggregator, logStateChange, getPlayerStats, getRealTimeAnalytics, EventType };
