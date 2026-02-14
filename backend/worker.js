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
import { processGameState } from './gameState.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** In-memory word list (lazy-loaded from data/words.txt). @type {string[]} */
let dictionary = [];

/** Load dictionary from data/words.txt. Uses fallback if file missing. */
function loadDictionary() {
  if (dictionary.length > 0) return dictionary;
  try {
    const path = join(__dirname, 'data', 'words.txt');
    const text = readFileSync(path, 'utf8');
    dictionary = text
      .split(/\r?\n/)
      .map((w) => w.trim().toLowerCase())
      .filter((w) => /^[a-z]{2,}$/.test(w));
  } catch {
    dictionary = getFallbackWords();
  }
  return dictionary;
}

/** Minimal fallback when data/words.txt is missing */
function getFallbackWords() {
  const raw =
    'act cat dog god eat tea ate sea see able bail beat care dare deal each idea lead read care deal earl hear bear rare tear acre race cat dog god act tea eat ate';
  return [...new Set(raw.split(/\s+/).filter((w) => w.length >= 2))];
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
      result = processGameState(payload, loadDictionary());
    } else if (kind === 'image') {
      result = processImageUpdate(payload);
    } else {
      result = { type: 'unknown', timestamp: Date.now(), data: payload, processed: false };
    }
    parentPort.postMessage({ ok: true, result });
  } catch (err) {
    parentPort.postMessage({ ok: false, error: err.message });
  }
});
