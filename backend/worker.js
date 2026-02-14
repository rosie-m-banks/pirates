import { parentPort } from 'worker_threads';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** @type {string[]} */
let dictionary = [];

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

/**
 * Letter counts for a string (lowercase, a-z only).
 * @param {string} str
 * @returns {Record<string, number>}
 */
function letterCounts(str) {
  const normalized = (str || '').toLowerCase().replace(/[^a-z]/g, '');
  const counts = {};
  for (const ch of normalized) counts[ch] = (counts[ch] || 0) + 1;
  return counts;
}

/**
 * True if word can be formed from the given letter counts (each letter of word used at most available count).
 * @param {Record<string, number>} available
 * @param {string} word
 */
function canForm(available, word) {
  const need = letterCounts(word);
  for (const ch of Object.keys(need)) {
    if ((available[ch] || 0) < need[ch]) return false;
  }
  return true;
}

/**
 * Find all dictionary words that can be formed from the given letters (anagrams and sub-anagrams).
 * @param {string} letters
 * @param {string[]} dict
 * @returns {string[]}
 */
function findAnagrams(letters, dict) {
  const available = letterCounts(letters);
  const found = [];
  const seen = new Set();
  for (const w of dict) {
    if (w.length > letters.length) continue;
    if (!canForm(available, w)) continue;
    const key = [...w].sort().join('');
    if (seen.has(key)) continue;
    seen.add(key);
    found.push(w);
  }
  return found.sort();
}

/**
 * Normalize payload into: wordsPerPlayer (array of string[]), availableLetters (string).
 * Accepts: { players: [{ words: [] }], availableLetters } or { wordsPerPlayer, availableLetters } etc.
 */
function normalizeGameData(payload) {
  const players = payload?.players ?? payload?.wordsPerPlayer ?? [];
  const wordsPerPlayer = Array.isArray(players)
    ? players.map((p) => (Array.isArray(p?.words) ? p.words : Array.isArray(p) ? p : []).map(String))
    : [];
  let availableLetters = payload?.availableLetters ?? payload?.available ?? '';
  if (Array.isArray(availableLetters)) availableLetters = availableLetters.join('');
  availableLetters = String(availableLetters).toLowerCase().replace(/[^a-z]/g, '');
  return { wordsPerPlayer, availableLetters };
}

/**
 * Process game state: load words per player and available letters, run anagram solver on
 * available letters, each word, every word pair, and return all words that can be made.
 */
function processGameState(payload) {
  const dict = loadDictionary();
  const { wordsPerPlayer, availableLetters } = normalizeGameData(payload);

  const result = {
    type: 'game-state',
    timestamp: Date.now(),
    data: payload,
    processed: true,
    anagrams: {
      fromAvailableLetters: [],
      fromWords: {},
      fromWordPairs: {},
      fromLetterSets: {},
      allFound: [],
    },
  };

  const allFoundSet = new Set();

  // 1) Anagram the available letters (full pool)
  if (availableLetters.length > 0) {
    const words = findAnagrams(availableLetters, dict);
    result.anagrams.fromAvailableLetters = words;
    words.forEach((w) => allFoundSet.add(w));
  }

  // 2) For each player, collect all words and anagram each word and every word pair
  const letterSetsTried = new Set();

  wordsPerPlayer.forEach((wordList, playerIndex) => {
    const playerWords = wordList.map((w) => String(w).toLowerCase().replace(/[^a-z]/g, '')).filter(Boolean);
    const playerKey = `player_${playerIndex}`;

    for (const w of playerWords) {
      if (!w) continue;
      const key = [...w].sort().join('');
      if (letterSetsTried.has(key)) continue;
      letterSetsTried.add(key);
      const words = findAnagrams(w, dict);
      result.anagrams.fromWords[w] = words;
      words.forEach((x) => allFoundSet.add(x));
    }

    for (let i = 0; i < playerWords.length; i++) {
      for (let j = i + 1; j < playerWords.length; j++) {
        const combined = playerWords[i] + playerWords[j];
        const pairKey = [playerWords[i], playerWords[j]].sort().join('+');
        const lettersKey = [...combined].sort().join('');
        if (letterSetsTried.has(lettersKey)) continue;
        letterSetsTried.add(lettersKey);
        const words = findAnagrams(combined, dict);
        result.anagrams.fromWordPairs[pairKey] = words;
        words.forEach((x) => allFoundSet.add(x));
      }
    }
  });

  // 3) "Every set of letters" = also try available letters combined with each single word (and optionally each pair)
  if (availableLetters.length > 0) {
    const poolKey = [...availableLetters].sort().join('');
    if (!letterSetsTried.has(poolKey)) {
      letterSetsTried.add(poolKey);
      const words = findAnagrams(availableLetters, dict);
      result.anagrams.fromLetterSets['available'] = words;
      words.forEach((x) => allFoundSet.add(x));
    }

    wordsPerPlayer.flat().forEach((w) => {
      const normalized = String(w).toLowerCase().replace(/[^a-z]/g, '');
      if (!normalized) return;
      const combined = availableLetters + normalized;
      const lettersKey = [...combined].sort().join('');
      if (letterSetsTried.has(lettersKey)) return;
      letterSetsTried.add(lettersKey);
      const words = findAnagrams(combined, dict);
      result.anagrams.fromLetterSets[`available+${normalized}`] = words;
      words.forEach((x) => allFoundSet.add(x));
    });
  }

  result.anagrams.allFound = [...allFoundSet].sort();

  return result;
}

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

parentPort.on('message', (msg) => {
  try {
    const { kind, payload } = msg;
    let result;
    if (kind === 'game-state') {
      result = processGameState(payload);
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
