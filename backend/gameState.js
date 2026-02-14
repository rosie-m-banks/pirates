/**
 * Game state logic for Pirates: normalize payload, find formable words, and build recommended_words
 * with valid constructions (full words + letters, ≥2 blocks, word length ≥3).
 * Used by worker.js and tests.
 *
 * Performance: single dict pass; no formable list/sort; mask loop high→low (no sort);
 * canFormFromCounts/countsEqual avoid string allocs; letters-only fast path; precomputed
 * playerWordCounts; first-letter quick reject; remainderStr built only on return.
 */

/**
 * Letter counts for a string (lowercase, a-z only).
 * @param {string} str
 * @returns {Record<string, number>}
 */
export function letterCounts(str) {
  const normalized = (str || '').toLowerCase().replace(/[^a-z]/g, '');
  const counts = {};
  for (const ch of normalized) counts[ch] = (counts[ch] || 0) + 1;
  return counts;
}

/**
 * True if word can be formed from the given letter counts.
 * @param {Record<string, number>} available
 * @param {string} word
 */
export function canForm(available, word) {
  const need = letterCounts(word);
  for (const ch of Object.keys(need)) {
    if ((available[ch] || 0) < need[ch]) return false;
  }
  return true;
}

/**
 * True if needCounts can be formed from available (compare two count objects, no string alloc).
 * @param {Record<string, number>} available
 * @param {Record<string, number>} needCounts
 */
function canFormFromCounts(available, needCounts) {
  for (const ch of Object.keys(needCounts || {})) {
    if ((available[ch] || 0) < needCounts[ch]) return false;
  }
  return true;
}

/**
 * True if two count objects are equal (same multiset of letters).
 */
function countsEqual(a, b) {
  const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
  for (const ch of keys) {
    if ((a[ch] || 0) !== (b[ch] || 0)) return false;
  }
  return true;
}

/**
 * Find all dictionary words that can be formed from the given letter counts.
 */
export function findFormableWords(availableCounts, dict, minLength = 1) {
  const total = Object.values(availableCounts).reduce((s, n) => s + n, 0);
  const found = [];
  for (const w of dict) {
    if (w.length < minLength || w.length > total) continue;
    if (!canForm(availableCounts, w)) continue;
    found.push(w);
  }
  return found.sort();
}

/**
 * Subtract letter counts: a - b (per letter, min 0).
 * @param {Record<string, number>} a
 * @param {Record<string, number>} b
 * @returns {Record<string, number>}
 */
export function subtractCounts(a, b) {
  const out = { ...a };
  for (const ch of Object.keys(b || {})) {
    out[ch] = Math.max(0, (out[ch] || 0) - (b[ch] || 0));
    if (out[ch] === 0) delete out[ch];
  }
  return out;
}

/**
 * Turn letter counts into a string.
 * @param {Record<string, number>} counts
 * @returns {string}
 */
export function countsToString(counts) {
  return Object.entries(counts || {})
    .flatMap(([ch, n]) => Array(n).fill(ch))
    .join('');
}

/**
 * Find one valid construction for target word: list of full player words + single letters.
 * Rules: (1) only additive — at least 2 blocks; (2) when using a word, use all its letters;
 * (3) letters-only construction that is an anagram of a single player word is invalid;
 * (4) remainder (letters not from chosen words) must be formable from available letters ONLY.
 * Prefer constructions that use more player words (iterate mask high→low = more bits first).
 * @param {string} target
 * @param {string[]} playerWordsUnique
 * @param {Record<string, number>} poolCounts full pool (for checking target is formable overall)
 * @param {Record<string, number>} availableCounts only loose/free letters (remainder must come from here)
 * @param {Record<string, number>[]} playerWordCounts precomputed letterCounts for each player word (optional; computed if not provided)
 * @returns {string[] | null}
 */
export function findOneConstruction(target, playerWordsUnique, poolCounts, availableCounts, playerWordCounts = null) {
  const targetCounts = letterCounts(target);
  const minBlocks = 2;
  const n = playerWordsUnique.length;
  const wordCounts = playerWordCounts ?? playerWordsUnique.map((w) => letterCounts(w));

  // Fast path: letters-only (mask 0). Avoids 2^n loop when word is buildable from available only.
  if (canFormFromCounts(availableCounts, targetCounts)) {
    const remainderLen = Object.values(targetCounts).reduce((s, x) => s + x, 0);
    if (remainderLen >= minBlocks) {
      const isAnagramOfOneWord = n > 0 && wordCounts.some((wc) => countsEqual(targetCounts, wc));
      if (!isAnagramOfOneWord) {
        const remainderStr = countsToString(targetCounts);
        return [...remainderStr.split('')];
      }
    }
  }

  for (let mask = (1 << n) - 1; mask >= 0; mask--) {
    let fromWordsCounts = {};
    const wordsUsed = [];
    for (let i = 0; i < n; i++) {
      if (!(mask & (1 << i))) continue;
      const wc = wordCounts[i];
      for (const ch of Object.keys(wc)) {
        fromWordsCounts[ch] = (fromWordsCounts[ch] || 0) + wc[ch];
      }
      wordsUsed.push(playerWordsUnique[i]);
    }
    let valid = true;
    for (const ch of Object.keys(fromWordsCounts)) {
      if ((targetCounts[ch] || 0) < fromWordsCounts[ch]) {
        valid = false;
        break;
      }
    }
    if (!valid) continue;

    const remainderCounts = subtractCounts(targetCounts, fromWordsCounts);
    if (!canFormFromCounts(availableCounts, remainderCounts)) continue;

    const remainderLen = Object.values(remainderCounts).reduce((s, n) => s + n, 0);
    const numBlocks = wordsUsed.length + remainderLen;
    if (numBlocks < minBlocks) continue;

    if (wordsUsed.length === 0 && remainderLen > 0) {
      const isAnagramOfOneWord = wordCounts.some((wc) => countsEqual(remainderCounts, wc));
      if (isAnagramOfOneWord) continue;
    }

    const remainderStr = countsToString(remainderCounts);
    return [...wordsUsed, ...remainderStr.split('')];
  }
  return null;
}

/**
 * Normalize payload into: wordsPerPlayer (array of string[]), availableLetters (string).
 */
export function normalizeGameData(payload) {
  const players = payload?.players ?? payload?.wordsPerPlayer ?? [];
  const wordsPerPlayer = Array.isArray(players)
    ? players.map((p) => (Array.isArray(p?.words) ? p.words : Array.isArray(p) ? p : []).map(String))
    : [];
  let availableLetters = payload?.availableLetters ?? payload?.available ?? '';
  if (Array.isArray(availableLetters)) availableLetters = availableLetters.join('');
  availableLetters = String(availableLetters).toLowerCase().replace(/[^a-z]/g, '');
  return { wordsPerPlayer, availableLetters };
}

export const MIN_WORD_LENGTH = 3;

/**
 * Process game state. Returns { players, recommended_words, availableLetters }.
 * @param {object} payload
 * @param {string[]} dict - dictionary (required; pass from loader in worker)
 */
export function processGameState(payload, dict) {
  const { wordsPerPlayer, availableLetters } = normalizeGameData(payload);

  const players = wordsPerPlayer.map((words) => ({ words: [...words] }));
  const recommended_words = {};

  const availableCounts = letterCounts(availableLetters);
  const poolCounts = { ...availableCounts };
  const allPlayerWords = [];
  wordsPerPlayer.flat().forEach((w) => {
    const normalized = String(w).toLowerCase().replace(/[^a-z]/g, '');
    if (!normalized) return;
    allPlayerWords.push(normalized);
    const wc = letterCounts(normalized);
    for (const ch of Object.keys(wc)) {
      poolCounts[ch] = (poolCounts[ch] || 0) + wc[ch];
    }
  });

  const playerWordsUnique = [...new Set(allPlayerWords)];
  const totalPool = Object.values(poolCounts).reduce((s, n) => s + n, 0);
  const playerWordCounts = playerWordsUnique.map((w) => letterCounts(w));

  for (const word of dict) {
    if (word.length < MIN_WORD_LENGTH || word.length > totalPool) continue;
    if (!poolCounts[word[0]]) continue;
    if (!canForm(poolCounts, word)) continue;
    const construction = findOneConstruction(word, playerWordsUnique, poolCounts, availableCounts, playerWordCounts);
    if (construction) recommended_words[word] = construction;
  }

  return {
    players,
    recommended_words,
    availableLetters,
  };
}
