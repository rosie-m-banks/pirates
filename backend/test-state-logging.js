/**
 * Test script for state logging functionality
 * Run with: node test-state-logging.js
 */

import {
    logStateChange,
    getPlayerStats,
    getRealTimeAnalytics,
    EventType,
} from "./stateLogger.js";

console.log("Testing State Logger...\n");

// Test 1: Log word additions for Player 0
console.log("Test 1: Logging word additions for Player 0...");
logStateChange({
    playerId: "player_0",
    word: "cat",
    wordLength: 3,
    frequencyScore: 6.5,
    lettersUsed: ["c", "a", "t"],
    eventType: EventType.WORD_ADDED,
    metadata: { availableLetters: "abcdefgh", playerIndex: 0 },
});

logStateChange({
    playerId: "player_0",
    word: "dog",
    wordLength: 3,
    frequencyScore: 6.2,
    lettersUsed: ["d", "o", "g"],
    eventType: EventType.WORD_ADDED,
    metadata: { availableLetters: "abcdefgh", playerIndex: 0 },
});

logStateChange({
    playerId: "player_0",
    word: "elephant",
    wordLength: 8,
    frequencyScore: 4.5,
    lettersUsed: ["e", "l", "e", "p", "h", "a", "n", "t"],
    eventType: EventType.WORD_ADDED,
    metadata: { availableLetters: "abcdefgh", playerIndex: 0 },
});

console.log("✓ Logged 3 word additions for Player 0\n");

// Test 1.5: Log word additions for Player 1
console.log("Test 1.5: Logging word additions for Player 1...");
logStateChange({
    playerId: "player_1",
    word: "bird",
    wordLength: 4,
    frequencyScore: 5.8,
    lettersUsed: ["b", "i", "r", "d"],
    eventType: EventType.WORD_ADDED,
    metadata: { availableLetters: "abcdefgh", playerIndex: 1 },
});

logStateChange({
    playerId: "player_1",
    word: "fish",
    wordLength: 4,
    frequencyScore: 5.5,
    lettersUsed: ["f", "i", "s", "h"],
    eventType: EventType.WORD_ADDED,
    metadata: { availableLetters: "abcdefgh", playerIndex: 1 },
});

console.log("✓ Logged 2 word additions for Player 1\n");

// Test 2: Get player statistics
console.log("Test 2: Retrieving player statistics...");
const playerStats = getPlayerStats("player_0");
console.log(JSON.stringify(playerStats, null, 2));
console.log();

// Test 3: Get real-time analytics
console.log("Test 3: Retrieving real-time analytics...");
const analytics = getRealTimeAnalytics();
console.log(JSON.stringify(analytics, null, 2));
console.log();

// Test 4: Log a word removal
console.log("Test 4: Logging word removal...");
logStateChange({
    playerId: "player_0",
    word: "cat",
    wordLength: 3,
    frequencyScore: 6.5,
    lettersUsed: [],
    eventType: EventType.WORD_REMOVED,
    metadata: { availableLetters: "abcdefgh" },
});
console.log("✓ Logged word removal\n");

// Test 5: Add more diverse words
console.log("Test 5: Adding diverse vocabulary...");
const testWords = [
    { word: "quick", length: 5, freq: 5.8 },
    { word: "brown", length: 5, freq: 5.2 },
    { word: "fox", length: 3, freq: 4.8 },
    { word: "jumps", length: 5, freq: 4.5 },
    { word: "lazy", length: 4, freq: 5.1 },
];

testWords.forEach(({ word, length, freq }) => {
    logStateChange({
        playerId: "player_0",
        word,
        wordLength: length,
        frequencyScore: freq,
        lettersUsed: word.split(""),
        eventType: EventType.WORD_ADDED,
        metadata: { availableLetters: "abcdefgh" },
    });
});

console.log(`✓ Logged ${testWords.length} more words\n`);

// Test 6: Final statistics
console.log("Test 6: Final statistics...");

// Player 0 stats
const finalStats0 = getPlayerStats("player_0");
console.log("Player 0 Stats:");
console.log(`  - Total words: ${finalStats0.totalWords}`);
console.log(`  - Unique words: ${finalStats0.uniqueWordsCount}`);
console.log(`  - Vocabulary diversity: ${(finalStats0.vocabularyDiversity * 100).toFixed(1)}%`);
console.log(`  - Avg word frequency (Zipf): ${finalStats0.avgWordFrequency.toFixed(2)}`);
console.log(`  - Vocabulary level: ${finalStats0.vocabularyLevel}`);
console.log(`  - Common words: ${finalStats0.wordsByFrequency.common}`);
console.log(`  - Medium words: ${finalStats0.wordsByFrequency.medium}`);
console.log(`  - Rare words: ${finalStats0.wordsByFrequency.rare}`);
console.log();

// Player 1 stats
const finalStats1 = getPlayerStats("player_1");
console.log("Player 1 Stats:");
console.log(`  - Total words: ${finalStats1.totalWords}`);
console.log(`  - Unique words: ${finalStats1.uniqueWordsCount}`);
console.log(`  - Vocabulary diversity: ${(finalStats1.vocabularyDiversity * 100).toFixed(1)}%`);
console.log(`  - Avg word frequency (Zipf): ${finalStats1.avgWordFrequency.toFixed(2)}`);
console.log(`  - Vocabulary level: ${finalStats1.vocabularyLevel}`);
console.log(`  - Common words: ${finalStats1.wordsByFrequency.common}`);
console.log(`  - Medium words: ${finalStats1.wordsByFrequency.medium}`);
console.log(`  - Rare words: ${finalStats1.wordsByFrequency.rare}`);
console.log();

// Overall analytics
const finalAnalytics = getRealTimeAnalytics();
console.log("Overall Analytics:");
console.log(`  - Total players: ${finalAnalytics.totalPlayers}`);
console.log(`  - Total unique words: ${finalAnalytics.totalUniqueWords}`);
console.log(
    `  - Session duration: ${(finalAnalytics.sessionDuration / 1000).toFixed(1)}s`,
);
console.log();

console.log("Top Words (All Players):");
finalAnalytics.topWords.forEach(({ word, count }) => {
    console.log(`  - ${word}: ${count} times`);
});

console.log("\n✅ All tests completed!");
console.log("\nCheck logs at:");
console.log("  - backend/logs/player_vocabulary.jsonl");
console.log("  - backend/logs/vocabulary_aggregate.json");
