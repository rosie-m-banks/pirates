/**
 * Game state logic for Pirates: normalize payload, find formable words, and build recommended_words
 * with valid constructions (full words + letters, ≥2 blocks, word length ≥3).
 * Letter counts use Uint8Array(26) for cache locality and O(26) hot-path ops.
 */

const A = 97; // 'a'.charCodeAt(0)
const LEN = 26;

/**
 * Letter counts for a string (lowercase, a-z only). Returns Uint8Array(26), index = charCode - 97.
 * @param {string} str
 * @returns {Uint8Array}
 */
export function letterCounts(str) {
  const normalized = (str || '').toLowerCase().replace(/[^a-z]/g, '');
  const counts = new Uint8Array(LEN);
  for (let i = 0; i < normalized.length; i++) {
    counts[normalized.charCodeAt(i) - A]++;
  }
  return counts;
}

/**
 * Sum of all counts in a 26-vector.
 * @param {Uint8Array} counts
 * @returns {number}
 */
function sumCounts(counts) {
  let s = 0;
  for (let i = 0; i < LEN; i++) s += counts[i];
  return s;
}

/**
 * True if word can be formed from the given letter counts (available is Uint8Array(26)).
 * @param {Uint8Array} available
 * @param {string} word
 */
export function canForm(available, word) {
  const need = letterCounts(word);
  for (let i = 0; i < LEN; i++) {
    if (available[i] < need[i]) return false;
  }
  return true;
}

/**
 * True if needCounts can be formed from available (both Uint8Array(26)). O(26), no alloc.
 * @param {Uint8Array} available
 * @param {Uint8Array} needCounts
 */
function canFormFromCounts(available, needCounts) {
  for (let i = 0; i < LEN; i++) {
    if (available[i] < needCounts[i]) return false;
  }
  return true;
}

/**
 * True if two count vectors are equal (same multiset of letters).
 * @param {Uint8Array} a
 * @param {Uint8Array} b
 */
function countsEqual(a, b) {
  for (let i = 0; i < LEN; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

/**
 * Find all dictionary words that can be formed from the given letter counts.
 * @param {Uint8Array} availableCounts
 */
export function findFormableWords(availableCounts, dict, minLength = 1) {
  const total = sumCounts(availableCounts);
  const found = [];
  for (const w of dict) {
    if (w.length < minLength || w.length > total) continue;
    if (!canForm(availableCounts, w)) continue;
    found.push(w);
  }
  return found.sort();
}

/**
 * Add two letter-count vectors (merge multisets). Returns new Uint8Array(26).
 * @param {Uint8Array} a
 * @param {Uint8Array} b
 * @returns {Uint8Array}
 */
function mergeCounts(a, b) {
  const out = new Uint8Array(LEN);
  for (let i = 0; i < LEN; i++) out[i] = a[i] + b[i];
  return out;
}

/**
 * Subtract letter counts: a - b (per index, min 0). Returns new Uint8Array(26).
 * @param {Uint8Array} a
 * @param {Uint8Array} b
 * @returns {Uint8Array}
 */
export function subtractCounts(a, b) {
  const out = new Uint8Array(LEN);
  for (let i = 0; i < LEN; i++) out[i] = Math.max(0, a[i] - b[i]);
  return out;
}

/**
 * Turn letter counts into a string (for construction array).
 * @param {Uint8Array} counts
 * @returns {string}
 */
export function countsToString(counts) {
  const parts = [];
  for (let i = 0; i < LEN; i++) {
    for (let k = 0; k < counts[i]; k++) parts.push(String.fromCharCode(A + i));
  }
  return parts.join('');
}

/**
 * Find one valid construction for target word: list of full player words + single letters.
 * All count args are Uint8Array(26). subsetCounts[mask] are Uint8Array(26).
 * @param {string} target
 * @param {string[]} playerWordsUnique
 * @param {Uint8Array} poolCounts
 * @param {Uint8Array} availableCounts
 * @param {Uint8Array[]} [playerWordCounts]
 * @param {Uint8Array} [targetCounts]
 * @param {Uint8Array[]} [subsetCounts]
 * @param {string[][]} [subsetWords]
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
    const remainderLen = sumCounts(targetCountsResolved);
    if (remainderLen >= minBlocks) {
      const isAnagramOfOneWord = n > 0 && wordCounts.some((wc) => countsEqual(targetCountsResolved, wc));
      if (!isAnagramOfOneWord) {
        const remainderStr = countsToString(targetCountsResolved);
        return [...remainderStr.split('')];
      }
    }
  }

  const numMasks = subsetCounts ? subsetCounts.length : 1 << n;
  const remainderBuf = new Uint8Array(LEN);
  for (let mask = numMasks - 1; mask >= 0; mask--) {
    const fromWordsCounts = subsetCounts ? subsetCounts[mask] : (() => {
      const c = new Uint8Array(LEN);
      for (let i = 0; i < n; i++) {
        if (!(mask & (1 << i))) continue;
        const wc = wordCounts[i];
        for (let j = 0; j < LEN; j++) c[j] += wc[j];
      }
      return c;
    })();
    const wordsUsed = subsetWords ? subsetWords[mask] : (() => {
      const w = [];
      for (let i = 0; i < n; i++) if (mask & (1 << i)) w.push(playerWordsUnique[i]);
      return w;
    })();

    let valid = true;
    for (let i = 0; i < LEN; i++) {
      if (targetCountsResolved[i] < fromWordsCounts[i]) {
        valid = false;
        break;
      }
    }
    if (!valid) continue;

    for (let i = 0; i < LEN; i++) remainderBuf[i] = Math.max(0, targetCountsResolved[i] - fromWordsCounts[i]);
    if (!canFormFromCounts(availableCounts, remainderBuf)) continue;

    const remainderLen = sumCounts(remainderBuf);
    const numBlocks = wordsUsed.length + remainderLen;
    if (numBlocks < minBlocks) continue;

    if (wordsUsed.length === 0 && remainderLen > 0) {
      const isAnagramOfOneWord = wordCounts.some((wc) => countsEqual(remainderBuf, wc));
      if (isAnagramOfOneWord) continue;
    }

    return [...wordsUsed, ...countsToString(remainderBuf).split('')];
  }
  return null;
}

/**
 * Precompute subset letter counts and words for masks 0..2^n-1 using Gray code order:
 * consecutive masks differ by one bit, so we update running counts in O(26) per mask. Total O(2^n).
 * subsetCounts[mask] is Uint8Array(26). Returns { subsetCounts, subsetWords, playerWordsUnique, playerWordCounts }.
 */
function precomputeSubsets(playerWordsUnique, playerWordCounts) {
  const n = playerWordsUnique.length;
  const numMasks = 1 << n;
  const subsetCounts = new Array(numMasks);
  const subsetWords = new Array(numMasks);
  const currentCounts = new Uint8Array(LEN);
  const currentWords = [];
  subsetCounts[0] = new Uint8Array(LEN);
  subsetWords[0] = [];
  let prevGray = 0;
  for (let k = 1; k < numMasks; k++) {
    const gray = k ^ (k >>> 1);
    const diff = prevGray ^ gray;
    let i = 0;
    while (diff !== (1 << i)) i++;
    if (gray & (1 << i)) {
      const wc = playerWordCounts[i];
      for (let j = 0; j < LEN; j++) currentCounts[j] += wc[j];
      currentWords.push(playerWordsUnique[i]);
    } else {
      const wc = playerWordCounts[i];
      for (let j = 0; j < LEN; j++) currentCounts[j] -= wc[j];
      currentWords.splice(currentWords.indexOf(playerWordsUnique[i]), 1);
    }
    subsetCounts[gray] = new Uint8Array(currentCounts);
    subsetWords[gray] = [...currentWords];
    prevGray = gray;
  }
  return { subsetCounts, subsetWords, playerWordsUnique, playerWordCounts };
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
 * When dictIndex is provided (wordsByFirstAndLength, maxWordLength), only words with first letter in pool
 * and length in [MIN_WORD_LENGTH, totalPool] are considered.
 * @param {object} payload
 * @param {string[]} dict - dictionary (required)
 * @param {Record<string, number>[]} [dictCounts] - precomputed letterCounts for each dict[i]
 * @param {{ wordsByFirstAndLength: Object, maxWordLength: number }} [dictIndex] - index by (first letter, length)
 * @param {Object} [subsetCache] - mutable cache { signature, subsetCounts, subsetWords, playerWordsUnique, playerWordCounts }; reuse when player words unchanged
 */
export function processGameState(payload, dict, dictCounts = null, dictIndex = null, subsetCache = null) {
  const { wordsPerPlayer, availableLetters } = normalizeGameData(payload);

  const players = wordsPerPlayer.map((words) => ({ words: [...words] }));
  const recommended_words = {};
  /** For each recommended word, how many letters you need to add (from available) to form it = stealability. */
  const lettersToSteal = {};

  const availableCounts = letterCounts(availableLetters);
  const poolCounts = new Uint8Array(availableCounts);
  const allPlayerWords = [];
  wordsPerPlayer.flat().forEach((w) => {
    const normalized = String(w).toLowerCase().replace(/[^a-z]/g, '');
    if (!normalized) return;
    allPlayerWords.push(normalized);
    const wc = letterCounts(normalized);
    for (let i = 0; i < LEN; i++) poolCounts[i] += wc[i];
  });

  const playerWordsUniqueFull = [...new Set(allPlayerWords)];
  const playerWordCountsFull = playerWordsUniqueFull.map((w) => letterCounts(w));
  const totalPool = sumCounts(poolCounts);

  const signature = playerWordsUniqueFull.slice().sort().join(',');
  let subsetCounts, subsetWords, playerWordsUnique, playerWordCounts;
  const cache = subsetCache;
  const nNew = playerWordsUniqueFull.length;
  const nOld = cache?.playerWordsUnique?.length ?? 0;
  const oldSet = nOld > 0 ? new Set(cache.playerWordsUnique) : new Set();
  const newWord = nNew === nOld + 1 ? playerWordsUniqueFull.find((w) => !oldSet.has(w)) : null;
  const canExtend =
    cache &&
    cache.subsetCounts &&
    nNew === nOld + 1 &&
    newWord != null &&
    playerWordsUniqueFull.every((w) => w === newWord || oldSet.has(w));
  if (canExtend) {
    const newWordCounts = letterCounts(newWord);
    const numMasksOld = 1 << nOld;
    const numMasksNew = 1 << nNew;
    subsetCounts = new Array(numMasksNew);
    subsetWords = new Array(numMasksNew);
    for (let mask = 0; mask < numMasksNew; mask++) {
      if (mask < numMasksOld) {
        subsetCounts[mask] = cache.subsetCounts[mask];
        subsetWords[mask] = cache.subsetWords[mask];
      } else {
        const oldMask = mask & (numMasksOld - 1);
        subsetCounts[mask] = mergeCounts(cache.subsetCounts[oldMask], newWordCounts);
        subsetWords[mask] = [...cache.subsetWords[oldMask], newWord];
      }
    }
    playerWordsUnique = [...cache.playerWordsUnique, newWord];
    playerWordCounts = [...cache.playerWordCounts, newWordCounts];
    if (cache) {
      cache.signature = signature;
      cache.subsetCounts = subsetCounts;
      cache.subsetWords = subsetWords;
      cache.playerWordsUnique = playerWordsUnique;
      cache.playerWordCounts = playerWordCounts;
    }
  } else if (cache && cache.signature === signature && cache.subsetCounts) {
    subsetCounts = cache.subsetCounts;
    subsetWords = cache.subsetWords;
    playerWordsUnique = cache.playerWordsUnique;
    playerWordCounts = cache.playerWordCounts;
  } else {
    const pre = precomputeSubsets(playerWordsUniqueFull, playerWordCountsFull);
    subsetCounts = pre.subsetCounts;
    subsetWords = pre.subsetWords;
    playerWordsUnique = pre.playerWordsUnique;
    playerWordCounts = pre.playerWordCounts;
    if (cache) {
      cache.signature = signature;
      cache.subsetCounts = subsetCounts;
      cache.subsetWords = subsetWords;
      cache.playerWordsUnique = playerWordsUnique;
      cache.playerWordCounts = playerWordCounts;
    }
  }

  const maxLen = Math.min(
    totalPool,
    dictIndex?.maxWordLength ?? Infinity
  );

  function* candidateIndices() {
    if (dictIndex?.wordsByFirstAndLength) {
      for (let c = 0; c < LEN; c++) {
        if (!poolCounts[c]) continue;
        const ch = String.fromCharCode(A + c);
        const byLen = dictIndex.wordsByFirstAndLength[ch];
        if (!byLen) continue;
        for (let len = MIN_WORD_LENGTH; len <= maxLen; len++) {
          const indices = byLen[len];
          if (indices) for (let j = 0; j < indices.length; j++) yield indices[j];
        }
      }
    } else {
      for (let i = 0; i < dict.length; i++) yield i;
    }
  }

  for (const i of candidateIndices()) {
    const word = dict[i];
    if (word.length < MIN_WORD_LENGTH || word.length > totalPool) continue;
    if (!poolCounts[word.charCodeAt(0) - A]) continue;
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
    if (construction) {
      recommended_words[word] = construction;
      lettersToSteal[word] = construction.filter((b) => b.length === 1).length;
    }
  }

  return {
    players,
    recommended_words,
    lettersToSteal,
    availableLetters,
  };
}
