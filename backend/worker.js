/**
 * Worker thread: loads dictionary, finds valid constructions for the Pirates tile game, and handles image updates.
 * Game-state result: { players, recommended_words, availableLetters }. Recommended words are only those
 * that can be built by adding full words and/or letters (≥2 building blocks, word length ≥3).
 * Communicates with the main thread via parentPort messages: { kind, payload } -> { ok, result/error }.
 */
import { parentPort } from 'worker_threads';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { processGameState, letterCounts, normalizeGameData } from './gameState.js';
import { fuseData, FreeListTracker, WordConfidenceTracker, WordVisibilityTracker } from './dataFusion.js';
import { sortRecommendations, ScoringConfig } from './recommendationScorer.js';
import { logStateChange, EventType, getAggregator } from './stateLogger.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** @type {{ words: string[], counts: Record<string, number>[], wordsByFirstAndLength: Object, maxWordLength: number, frequencies: Record<string, number> }} */
let dictionaryCache = null;

/** Build index: wordsByFirstAndLength[firstLetter][length] = array of dict indices. */
function buildWordsByFirstAndLength(words) {
  const index = {};
  let maxWordLength = 0;
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    if (w.length < 2) continue;
    const c = w[0];
    const len = w.length;
    if (len > maxWordLength) maxWordLength = len;
    if (!index[c]) index[c] = {};
    if (!index[c][len]) index[c][len] = [];
    index[c][len].push(i);
  }
  return { wordsByFirstAndLength: index, maxWordLength };
}

/** Load dictionary, precompute letter counts and index by (first letter, length). O(D*L) at load. */
function loadDictionary() {
  if (dictionaryCache) return dictionaryCache;
  let words = [];
  try {
    const path = join(__dirname, 'data', 'words.txt');
    const text = readFileSync(path, 'utf8');
    words = text
      .split(/\r?\n/)
      .map((w) => w.trim().toLowerCase())
      .filter((w) => /^[a-z]{2,}$/.test(w));
  } catch {
    words = getFallbackWords();
  }
  const counts = words.map((w) => letterCounts(w));
  const { wordsByFirstAndLength, maxWordLength } = buildWordsByFirstAndLength(words);

  // Load word frequencies (zipf scores 0-8, higher = more common)
  let frequencies = {};
  try {
    const freqPath = join(__dirname, 'data', 'word_frequencies.json');
    const freqText = readFileSync(freqPath, 'utf8');
    frequencies = JSON.parse(freqText);
  } catch {
    // Fallback: no frequency sorting if file missing
    console.warn('word_frequencies.json not found, recommendations will not be sorted by frequency');
  }

  dictionaryCache = { words, counts, wordsByFirstAndLength, maxWordLength, frequencies };
  return dictionaryCache;
}

/** Minimal fallback when data/words.txt is missing */
function getFallbackWords() {
  const raw =
    'act cat dog god eat tea ate sea see able bail beat care dare deal each idea lead read care deal earl hear bear rare tear acre race cat dog god act tea eat ate';
  return [...new Set(raw.split(/\s+/).filter((w) => w.length >= 2))];
}

/** Mutable cache keyed by player-words signature; reused when only available letters change. */
let subsetCache = {};
/** Last game state (for delta payloads). */
let lastState = null;
/** Previous fused state for data fusion (words and availableLetters). */
let previousFusedState = null;
/** Free list tracker for persistence tracking. */
let freeListTracker = new FreeListTracker();
/** Word confidence tracker for Kalman filter-like confidence tracking. */
let confidenceTracker = new WordConfidenceTracker();
/** Word visibility tracker - removes words not seen in last 2 raw VLM calls. */
let wordVisibilityTracker = new WordVisibilityTracker();
/** Previous words per player for state change detection. Map<playerIndex, Set<word>> */
let previousWordsByPlayer = new Map();

/**
 * Apply delta to last state, or use full payload. Returns payload to pass to processGameState.
 * Delta format: { addedWords?: string[], removedWords?: string[], availableLetters?: string }.
 */
function applyPayload(payload) {
  if (payload.addedWords != null || payload.removedWords != null) {
    const prev = lastState ?? { wordsPerPlayer: [[]], availableLetters: '' };
    const words = [...prev.wordsPerPlayer.flat()];
    for (const w of payload.removedWords ?? []) {
      const i = words.indexOf(w);
      if (i >= 0) words.splice(i, 1);
    }
    for (const w of payload.addedWords ?? []) words.push(w);
    const availableLetters = payload.availableLetters ?? prev.availableLetters;
    lastState = { wordsPerPlayer: [words], availableLetters };
    return { players: [{ words }], availableLetters };
  }
  const { wordsPerPlayer, availableLetters } = normalizeGameData(payload);
  lastState = { wordsPerPlayer, availableLetters };
  return payload;
}

/**
 * Detect and log word additions/removals per player between states
 * @param {string[][]} wordsPerPlayer - Current words per player (array of word arrays)
 * @param {Map<number, Set<string>>} previousWordsByPlayer - Previous words per player
 * @param {Object} frequencies - Word frequency scores (zipf)
 * @param {string} availableLetters - Current available letters
 * @returns {Object} - Summary of changes per player
 */
function detectAndLogStateChanges(wordsPerPlayer, previousWordsByPlayer, frequencies, availableLetters) {
  const changesSummary = {
    totalAdded: 0,
    totalRemoved: 0,
    byPlayer: []
  };

  // Process each player
  for (let playerIndex = 0; playerIndex < wordsPerPlayer.length; playerIndex++) {
    const playerId = `player_${playerIndex}`;
    const currentWords = wordsPerPlayer[playerIndex] || [];
    const previousWords = previousWordsByPlayer.get(playerIndex) || new Set();

    const currentSet = new Set(currentWords.map(w => w.toLowerCase()));

    // Detect newly added words for this player
    const addedWords = currentWords.filter(word => {
      const normalized = word.toLowerCase();
      return !previousWords.has(normalized);
    });

    // Log each added word with metadata
    for (const word of addedWords) {
      const normalized = word.toLowerCase();
      const wordLength = normalized.length;
      const frequencyScore = frequencies[normalized] || 0;
      const letterCount = letterCounts(normalized);

      // Determine which letters were likely used
      const lettersUsed = [];
      for (let i = 0; i < 26; i++) {
        if (letterCount[i] > 0) {
          const letter = String.fromCharCode(97 + i); // 'a' = 97
          for (let j = 0; j < letterCount[i]; j++) {
            lettersUsed.push(letter);
          }
        }
      }

      logStateChange({
        playerId,
        word: normalized,
        wordLength,
        frequencyScore,
        lettersUsed,
        eventType: EventType.WORD_ADDED,
        metadata: {
          availableLetters,
          playerIndex,
          timestamp: Date.now(),
        },
      });
    }

    // Detect removed words (for completeness)
    const removedWords = Array.from(previousWords).filter(word => !currentSet.has(word));
    for (const word of removedWords) {
      logStateChange({
        playerId,
        word,
        wordLength: word.length,
        frequencyScore: frequencies[word] || 0,
        lettersUsed: [],
        eventType: EventType.WORD_REMOVED,
        metadata: {
          availableLetters,
          playerIndex,
          timestamp: Date.now(),
        },
      });
    }

    changesSummary.totalAdded += addedWords.length;
    changesSummary.totalRemoved += removedWords.length;
    changesSummary.byPlayer.push({
      playerId,
      playerIndex,
      addedWords,
      removedWords,
      totalWords: currentWords.length
    });

    // Update previous words for this player
    previousWordsByPlayer.set(playerIndex, currentSet);
  }

  return changesSummary;
}

// Message handler: main thread sends { kind, payload }; we reply with { ok, result } or { ok: false, error }

/**
 * Process image update payload (e.g. metadata, dimensions, or pass-through).
 */
function processImageUpdate(payload) {
  return {
    type: 'image',
    timestamp: Date.now(),
    data: payload,
    processed: true,
  };
}

// Handle incoming messages: dispatch by kind, post result or error back to main thread
parentPort.on('message', (msg) => {
  try {
    const { kind, payload } = msg;
    let result;
    if (kind === 'game-state') {
      // Load dictionary and create Set for fast lookup
      const { words, counts, wordsByFirstAndLength, maxWordLength, frequencies } = loadDictionary();
      const dictSet = new Set(words);

      // Apply fusion to clean noisy vision data
      const fused = fuseData(payload, previousFusedState, dictSet, freeListTracker, confidenceTracker, wordVisibilityTracker);

      // Update previous fused state for next iteration
      const { wordsPerPlayer, availableLetters } = normalizeGameData(fused);

      // Detect and log state changes per player (word additions/removals)
      const changesSummary = detectAndLogStateChanges(
        wordsPerPlayer,
        previousWordsByPlayer,
        frequencies,
        availableLetters
      );

      // Update previous state trackers
      previousFusedState = {
        words: wordsPerPlayer.flat(),
        availableLetters: availableLetters,
      };
      // Note: previousWordsByPlayer is updated inside detectAndLogStateChanges

      // Apply delta logic if needed (for backward compatibility)
      const resolved = applyPayload(fused);


      result = processGameState(resolved, words, counts, { wordsByFirstAndLength, maxWordLength }, subsetCache);

      // Sort and filter recommended_words using modular scoring system
      if (result.recommended_words && Object.keys(frequencies).length > 0) {
        result.recommended_words = sortRecommendations(
          result.recommended_words,
          frequencies,
          ScoringConfig
        );
      }

      // Attach real-time analytics to result (optional, for debugging/monitoring)
      result._analytics = {
        changes: changesSummary,
        vocabularyStats: getAggregator().getRealTimeAnalytics(),
      };
    } else if (kind === 'image') {
      result = processImageUpdate(payload);
    } else if (kind === 'analytics') {
      // Return real-time vocabulary analytics
      result = getAggregator().getRealTimeAnalytics();
    } else if (kind === 'player-stats') {
      // Return stats for a specific player
      const { playerId = 'player_0' } = payload;
      result = getAggregator().getPlayerVocabularyStats(playerId);
    } else {
      result = { type: 'unknown', timestamp: Date.now(), data: payload, processed: false };
    }
    parentPort.postMessage({ ok: true, result });
  } catch (err) {
    parentPort.postMessage({ ok: false, error: err.message });
  }
});
