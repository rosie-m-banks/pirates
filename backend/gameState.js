/**
 * Game state logic for Pirates: normalize payload, find formable words, and build recommended_words
 * with valid constructions (full words + letters, ≥2 blocks, word length ≥3).
 * Used by worker.js and tests.
 *
 * Big O (per request): O(D) formability + O(2^min(n,K)) precompute + O(F·2^min(n,K)) constructions
 * (D=dict size, F=formable words, n=player words, K=16). Precomputed dict counts and subset
 * counts remove O(L) and O(n) from inner loops; cap n so 2^n is constant.
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
 * Add two letter-count objects (merge multisets).
 * @param {Record<string, number>} a
 * @param {Record<string, number>} b
 * @returns {Record<string, number>}
 */
function mergeCounts(a, b) {
  const out = { ...a };
  for (const ch of Object.keys(b || {})) {
    out[ch] = (out[ch] || 0) + b[ch];
  }
  return out;
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
 * When subsetCounts/subsetWords are provided (from precomputeSubsets), inner loop is O(1) per mask
 * instead of O(n). When targetCounts is provided, skips letterCounts(target).
 * @param {string} target
 * @param {string[]} playerWordsUnique
 * @param {Record<string, number>} poolCounts
 * @param {Record<string, number>} availableCounts
 * @param {Record<string, number>[]} [playerWordCounts]
 * @param {Record<string, number>} [targetCounts] precomputed letterCounts(target)
 * @param {Record<string, number>[]} [subsetCounts] precomputed counts per mask, length 2^n
 * @param {string[][]} [subsetWords] precomputed words per mask, length 2^n
 * @returns {string[] | null}
 */
export function findOneConstruction(
  target,
  playerWordsUnique,
  poolCounts,
  availableCounts,
  playerWordCounts = null,
  targetCounts = null,
  subsetCounts = null,
  subsetWords = null
) {
  const targetCountsResolved = targetCounts ?? letterCounts(target);
  const minBlocks = 2;
  const n = playerWordsUnique.length;
  const wordCounts = playerWordCounts ?? playerWordsUnique.map((w) => letterCounts(w));

  if (canFormFromCounts(availableCounts, targetCountsResolved)) {
    const remainderLen = Object.values(targetCountsResolved).reduce((s, x) => s + x, 0);
    if (remainderLen >= minBlocks) {
      const isAnagramOfOneWord = n > 0 && wordCounts.some((wc) => countsEqual(targetCountsResolved, wc));
      if (!isAnagramOfOneWord) {
        const remainderStr = countsToString(targetCountsResolved);
        return [...remainderStr.split('')];
      }
    }
  }

  const numMasks = subsetCounts ? subsetCounts.length : 1 << n;
  for (let mask = numMasks - 1; mask >= 0; mask--) {
    const fromWordsCounts = subsetCounts ? subsetCounts[mask] : (() => {
      const c = {};
      for (let i = 0; i < n; i++) {
        if (!(mask & (1 << i))) continue;
        const wc = wordCounts[i];
        for (const ch of Object.keys(wc)) c[ch] = (c[ch] || 0) + wc[ch];
      }
      return c;
    })();
    const wordsUsed = subsetWords ? subsetWords[mask] : (() => {
      const w = [];
      for (let i = 0; i < n; i++) if (mask & (1 << i)) w.push(playerWordsUnique[i]);
      return w;
    })();

    let valid = true;
    for (const ch of Object.keys(fromWordsCounts)) {
      if ((targetCountsResolved[ch] || 0) < fromWordsCounts[ch]) {
        valid = false;
        break;
      }
    }
    if (!valid) continue;

    const remainderCounts = subtractCounts(targetCountsResolved, fromWordsCounts);
    if (!canFormFromCounts(availableCounts, remainderCounts)) continue;

    const remainderLen = Object.values(remainderCounts).reduce((s, x) => s + x, 0);
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
 * Precompute subset letter counts and words for masks 0..2^n-1. Caps n at MAX_PLAYER_WORDS_FOR_SUBSETS.
 * Returns { subsetCounts, subsetWords, playerWordsUnique, playerWordCounts } (possibly truncated).
 * O(2^n * n) once per game state; then findOneConstruction is O(2^n) per word with O(1) per mask.
 */
function precomputeSubsets(playerWordsUnique, playerWordCounts) {
  const cap = Math.min(playerWordsUnique.length, MAX_PLAYER_WORDS_FOR_SUBSETS);
  const byLen = playerWordsUnique
    .map((w, i) => ({ w, i }))
    .sort((a, b) => b.w.length - a.w.length);
  const truncated = byLen.slice(0, cap).map((x) => x.w);
  const truncatedCounts = byLen.slice(0, cap).map((x) => playerWordCounts[x.i]);
  const n = truncated.length;
  const numMasks = 1 << n;
  const subsetCounts = [];
  const subsetWords = [];
  for (let mask = 0; mask < numMasks; mask++) {
    let c = {};
    const words = [];
    for (let i = 0; i < n; i++) {
      if (!(mask & (1 << i))) continue;
      c = mergeCounts(c, truncatedCounts[i]);
      words.push(truncated[i]);
    }
    subsetCounts[mask] = c;
    subsetWords[mask] = words;
  }
  return { subsetCounts, subsetWords, playerWordsUnique: truncated, playerWordCounts: truncatedCounts, n };
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

/** Max player words used for subset enumeration (caps 2^n for O(1) subset count per game). */
const MAX_PLAYER_WORDS_FOR_SUBSETS = 16;

/**
 * Process game state. Returns { players, recommended_words, availableLetters }.
 * Big O: O(D) formability + O(2^min(n,K)) precompute + O(F * 2^min(n,K)) constructions,
 * with K=MAX_PLAYER_WORDS_FOR_SUBSETS. Use dictCounts when available for O(1) formability per word.
 * @param {object} payload
 * @param {string[]} dict - dictionary (required)
 * @param {Record<string, number>[]} [dictCounts] - precomputed letterCounts for each dict[i]; if provided, formability is O(1) per word
 */
export function processGameState(payload, dict, dictCounts = null) {
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

  const playerWordsUniqueFull = [...new Set(allPlayerWords)];
  const playerWordCountsFull = playerWordsUniqueFull.map((w) => letterCounts(w));
  const totalPool = Object.values(poolCounts).reduce((s, n) => s + n, 0);

  const { subsetCounts, subsetWords, playerWordsUnique, playerWordCounts } = precomputeSubsets(
    playerWordsUniqueFull,
    playerWordCountsFull
  );

  for (let i = 0; i < dict.length; i++) {
    const word = dict[i];
    if (word.length < MIN_WORD_LENGTH || word.length > totalPool) continue;
    if (!poolCounts[word[0]]) continue;
    const wc = dictCounts ? dictCounts[i] : letterCounts(word);
    if (!canFormFromCounts(poolCounts, wc)) continue;
    const construction = findOneConstruction(
      word,
      playerWordsUnique,
      poolCounts,
      availableCounts,
      playerWordCounts,
      wc,
      subsetCounts,
      subsetWords
    );
    if (construction) recommended_words[word] = construction;
  }

  return {
    players,
    recommended_words,
    availableLetters,
  };
}
