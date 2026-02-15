/**
 * Data fusion module: cleans and validates noisy vision package data.
 * Applies corrections to player words and tracks free list letters.
 */
import { normalizeGameData } from './gameState.js';

const MIN_WORD_LENGTH = 3;

/**
 * Check if a word exists in the dictionary (case-insensitive).
 */
function isRealWord(word, dictSet) {
  return dictSet.has(word.toLowerCase());
}

/**
 * Check if word is one letter off from any word in previous list.
 * Returns the corrected word if found, null otherwise.
 * Prefers the previous word if it's a real word (VLM probably just missed a letter).
 */
function checkOneLetterOff(word, previousWords, dictSet) {
  const lower = word.toLowerCase();
  for (const prevWord of previousWords) {
    const prevLower = prevWord.toLowerCase();
    if (Math.abs(lower.length - prevLower.length) !== 1) continue;
    
    // Check if adding/removing one letter makes them match
    const shorter = lower.length < prevLower.length ? lower : prevLower;
    const longer = lower.length > prevLower.length ? lower : prevLower;
    
    // Try removing each letter from longer word
    for (let i = 0; i < longer.length; i++) {
      const candidate = longer.slice(0, i) + longer.slice(i + 1);
      if (candidate === shorter) {
        // Prefer the previous word if it's a real word (VLM probably missed a letter)
        if (isRealWord(prevLower, dictSet)) {
          return prevLower;
        }
        // Otherwise, if the shorter version is a real word, return it
        if (isRealWord(shorter, dictSet)) {
          return shorter;
        }
        // Otherwise, return the longer version if it's a real word
        if (isRealWord(longer, dictSet)) {
          return longer;
        }
      }
    }
  }
  return null;
}

/**
 * Check if word can be split into two real words.
 * Returns array of two words if found, null otherwise.
 * Prioritizes splits where one part matches a disappeared word.
 * Only returns splits where both parts are at least MIN_WORD_LENGTH.
 */
function checkSplitIntoTwoWords(word, dictSet, disappearedWords = []) {
  const lower = word.toLowerCase();
  const disappearedSet = new Set(disappearedWords.map(w => w.toLowerCase()));
  
  // First, check if any split matches a disappeared word
  for (let i = MIN_WORD_LENGTH; i <= lower.length - MIN_WORD_LENGTH; i++) {
    const part1 = lower.slice(0, i);
    const part2 = lower.slice(i);
    
    // Both parts must be at least MIN_WORD_LENGTH
    if (part1.length < MIN_WORD_LENGTH || part2.length < MIN_WORD_LENGTH) continue;
    
    const part1IsReal = isRealWord(part1, dictSet);
    const part2IsReal = isRealWord(part2, dictSet);
    
    // Prioritize if one part matches a disappeared word
    if ((disappearedSet.has(part1) && part2IsReal) || 
        (disappearedSet.has(part2) && part1IsReal)) {
      return [part1, part2];
    }
    
    // Also check if both are real words
    if (part1IsReal && part2IsReal) {
      // Store this as a candidate, but continue looking for disappeared word matches
      // We'll return the first valid split if no disappeared word match is found
    }
  }
  
  // If no disappeared word match, return any valid split
  for (let i = MIN_WORD_LENGTH; i <= lower.length - MIN_WORD_LENGTH; i++) {
    const part1 = lower.slice(0, i);
    const part2 = lower.slice(i);
    
    // Both parts must be at least MIN_WORD_LENGTH
    if (part1.length < MIN_WORD_LENGTH || part2.length < MIN_WORD_LENGTH) continue;
    
    if (isRealWord(part1, dictSet) && isRealWord(part2, dictSet)) {
      return [part1, part2];
    }
  }
  
  return null;
}

/**
 * Recursively split a long word that isn't a real word into multiple real words.
 * Returns array of words if successful, null otherwise.
 */
function checkRecursiveSplit(word, dictSet, disappearedWords = [], maxDepth = 3) {
  const lower = word.toLowerCase();
  if (lower.length < MIN_WORD_LENGTH * 2) return null; // Too short to split into 2 words
  
  // If it's already a real word, return it
  if (isRealWord(lower, dictSet)) {
    return [lower];
  }
  
  // Try splitting at each position
  for (let i = MIN_WORD_LENGTH; i <= lower.length - MIN_WORD_LENGTH; i++) {
    const part1 = lower.slice(0, i);
    const part2 = lower.slice(i);
    
    if (part1.length < MIN_WORD_LENGTH || part2.length < MIN_WORD_LENGTH) continue;
    
    const part1IsReal = isRealWord(part1, dictSet);
    const part2IsReal = isRealWord(part2, dictSet);
    
    if (part1IsReal && part2IsReal) {
      // Both parts are real words
      return [part1, part2];
    } else if (part1IsReal && maxDepth > 0) {
      // First part is real, try to split the second part recursively
      const splitPart2 = checkRecursiveSplit(part2, dictSet, disappearedWords, maxDepth - 1);
      if (splitPart2) {
        return [part1, ...splitPart2];
      }
    } else if (part2IsReal && maxDepth > 0) {
      // Second part is real, try to split the first part recursively
      const splitPart1 = checkRecursiveSplit(part1, dictSet, disappearedWords, maxDepth - 1);
      if (splitPart1) {
        return [...splitPart1, part2];
      }
    }
  }
  
  return null;
}

/**
 * Check if word looks like it was combined with another word.
 * Returns array of words if found, null otherwise.
 * Prioritizes matches with disappeared words.
 * Only returns splits where all parts are at least MIN_WORD_LENGTH.
 */
function checkCombinedWithWord(word, disappearedWords, dictSet) {
  const lower = word.toLowerCase();
  const disappearedSet = new Set(disappearedWords.map(w => w.toLowerCase()));
  
  // Check if word starts or ends with a disappeared word
  for (const disappearedWord of disappearedWords) {
    const disappearedLower = disappearedWord.toLowerCase();
    
    // Skip if disappeared word is too short
    if (disappearedLower.length < MIN_WORD_LENGTH) continue;
    
    // Check if word starts with disappeared word
    if (lower.startsWith(disappearedLower) && lower.length > disappearedLower.length) {
      const remainder = lower.slice(disappearedLower.length);
      // Check if remainder is at least MIN_WORD_LENGTH and is a real word OR another disappeared word
      if (remainder.length >= MIN_WORD_LENGTH && 
          (isRealWord(remainder, dictSet) || disappearedSet.has(remainder))) {
        return [disappearedWord, remainder];
      }
    }
    
    // Check if word ends with disappeared word
    if (lower.endsWith(disappearedLower) && lower.length > disappearedLower.length) {
      const remainder = lower.slice(0, lower.length - disappearedLower.length);
      // Check if remainder is at least MIN_WORD_LENGTH and is a real word OR another disappeared word
      if (remainder.length >= MIN_WORD_LENGTH && 
          (isRealWord(remainder, dictSet) || disappearedSet.has(remainder))) {
        return [remainder, disappearedWord];
      }
    }
    
    // Check if disappeared word is in the middle (less common but possible)
    const index = lower.indexOf(disappearedLower);
    if (index >= MIN_WORD_LENGTH && index + disappearedLower.length <= lower.length - MIN_WORD_LENGTH) {
      const before = lower.slice(0, index);
      const after = lower.slice(index + disappearedLower.length);
      // Check if both parts are at least MIN_WORD_LENGTH and are real words OR disappeared words
      if (before.length >= MIN_WORD_LENGTH && after.length >= MIN_WORD_LENGTH &&
          (isRealWord(before, dictSet) || disappearedSet.has(before)) && 
          (isRealWord(after, dictSet) || disappearedSet.has(after))) {
        return [before, disappearedWord, after];
      }
    }
  }
  
  return null;
}

/**
 * Check if adding one letter makes it a real word.
 * ONLY uses letters from free list first. Only tries common letters if no free list letter works.
 * Returns corrected word if found, null otherwise.
 */
function checkAddOneLetter(word, oldFreeList, dictSet) {
  const lower = word.toLowerCase();
  const freeListLetters = oldFreeList ? [...new Set(oldFreeList.toLowerCase().split('').filter(c => /[a-z]/.test(c)))] : [];
  
  // Common letters (ordered by frequency in English) - only used as fallback
  const commonLetters = ['e', 'a', 'r', 'i', 'o', 't', 'n', 's', 'l', 'c', 'u', 'd', 'p', 'm', 'h', 'g', 'b', 'f', 'y', 'w', 'k', 'v', 'x', 'z', 'j', 'q'];
  
  // Try positions: prefer middle positions
  const positions = [];
  for (let i = 0; i <= lower.length; i++) {
    // Middle positions first
    const distFromMiddle = Math.abs(i - lower.length / 2);
    positions.push({ pos: i, priority: distFromMiddle });
  }
  positions.sort((a, b) => a.priority - b.priority);
  
  // FIRST: Try ONLY free list letters
  if (freeListLetters.length > 0) {
    for (const { pos } of positions) {
      for (const letter of freeListLetters) {
        const candidate = lower.slice(0, pos) + letter + lower.slice(pos);
        if (isRealWord(candidate, dictSet)) {
          return candidate;
        }
      }
    }
  }
  
  // FALLBACK: Only if no free list letter worked, try common letters
  for (const { pos } of positions) {
    for (const letter of commonLetters) {
      const candidate = lower.slice(0, pos) + letter + lower.slice(pos);
      if (isRealWord(candidate, dictSet)) {
        return candidate;
      }
    }
  }
  
  return null;
}

/**
 * Correct a single word using all strategies.
 * Returns { word: string|string[], wasModified: boolean }
 */
function correctWord(word, previousWords, oldFreeList, dictSet, disappearedWords = []) {
  const normalized = word.toLowerCase().trim();
  if (!normalized) return { word: normalized, wasModified: false };
  
  // 1. Check if it's already a real word
  if (isRealWord(normalized, dictSet)) {
    return { word: normalized, wasModified: false };
  }
  
  // 2. PRIORITY: Check if word was combined with a disappeared word
  const combined = checkCombinedWithWord(normalized, disappearedWords, dictSet);
  if (combined) {
    // Return as array to indicate it should be split - this is a modification
    return { word: combined, wasModified: true };
  }
  
  // 3. Check if can be split into two words (prioritizing disappeared words)
  const split = checkSplitIntoTwoWords(normalized, dictSet, disappearedWords);
  if (split) {
    // Return as array to indicate it should be split - this is a modification
    return { word: split, wasModified: true };
  }
  
  // 4. For long words that aren't real, try recursive splitting
  if (normalized.length >= MIN_WORD_LENGTH * 2) {
    const recursiveSplit = checkRecursiveSplit(normalized, dictSet, disappearedWords);
    if (recursiveSplit && recursiveSplit.length > 1) {
      return { word: recursiveSplit, wasModified: true };
    }
  }
  
  // 5. Check if one letter off from previous word
  const oneLetterOff = checkOneLetterOff(normalized, previousWords, dictSet);
  if (oneLetterOff) {
    return { word: oneLetterOff, wasModified: true };
  }
  
  // 6. Check if adding one letter makes it real
  const withAddedLetter = checkAddOneLetter(normalized, oldFreeList, dictSet);
  if (withAddedLetter) {
    return { word: withAddedLetter, wasModified: true };
  }
  
  // If no correction found, return original (not modified, but also not a real word)
  return { word: normalized, wasModified: false };
}

/**
 * Track free list letters using a 2-call smoothing window.
 * Tracks the last 2 raw VLM calls to determine if letters should be kept.
 */
class FreeListTracker {
  constructor() {
    this.rawCalls = []; // Array of last 2 raw VLM free lists (before fusion)
    this.currentFreeList = ''; // Current fused free list
  }
  
  /**
   * Record a raw VLM call (before fusion).
   */
  recordRawCall(rawFreeList) {
    const normalized = (rawFreeList || '').toLowerCase();
    this.rawCalls.push(normalized);
    // Keep only last 2 calls
    if (this.rawCalls.length > 2) {
      this.rawCalls.shift();
    }
  }
  
  /**
   * Check if a letter was seen in the last 2 raw VLM calls.
   */
  wasSeenInLastTwoCalls(letter) {
    const lowerLetter = letter.toLowerCase();
    return this.rawCalls.some(call => call.includes(lowerLetter));
  }
  
  /**
   * Update the current fused free list.
   */
  update(newFreeList) {
    this.currentFreeList = newFreeList || '';
  }
  
  getOldFreeList() {
    return this.currentFreeList;
  }
}

/**
 * Track word visibility in the last 2 raw VLM calls.
 * Words that haven't appeared in the last 2 calls should be removed.
 */
class WordVisibilityTracker {
  constructor() {
    this.rawWordCalls = []; // Array of last 2 raw VLM word lists (before fusion)
  }
  
  /**
   * Record a raw VLM word list call (before fusion).
   */
  recordRawCall(rawWords) {
    const normalized = rawWords.map(w => w.toLowerCase().trim());
    this.rawWordCalls.push(normalized);
    // Keep only last 2 calls
    if (this.rawWordCalls.length > 2) {
      this.rawWordCalls.shift();
    }
  }
  
  /**
   * Check if a word was seen in the last 2 raw VLM calls.
   */
  wasSeenInLastTwoCalls(word) {
    const lowerWord = word.toLowerCase();
    return this.rawWordCalls.some(call => call.includes(lowerWord));
  }
}

/**
 * Track word confidence scores (Kalman filter-like approach).
 * Confidence: 1.0 = high confidence (observed directly), 0.5 = modified (low confidence), 0.0 = discarded
 */
class WordConfidenceTracker {
  constructor() {
    // Map<word, {confidence: number, wasModified: boolean}>
    this.wordConfidences = new Map();
  }
  
  /**
   * Get confidence for a word (default 1.0 if not tracked).
   */
  getConfidence(word) {
    const entry = this.wordConfidences.get(word.toLowerCase());
    return entry ? entry.confidence : 1.0;
  }
  
  /**
   * Check if a word was previously modified.
   */
  wasModified(word) {
    const entry = this.wordConfidences.get(word.toLowerCase());
    return entry ? entry.wasModified : false;
  }
  
  /**
   * Update confidence for words based on current observations.
   * - If word is observed directly (not modified), increase confidence
   * - If word was modified, set confidence to 0.5
   * - If word is not observed, decrease confidence slightly (but keep for smoothing)
   */
  update(currentWords, modifiedWords) {
    const currentWordsSet = new Set(currentWords.map(w => w.toLowerCase()));
    const modifiedWordsSet = new Set(modifiedWords.map(w => w.toLowerCase()));
    
    // Update confidence for current words
    for (const word of currentWords) {
      const lower = word.toLowerCase();
      const wasModified = modifiedWordsSet.has(lower);
      
      if (wasModified) {
        // Word was modified - set confidence to 0.5
        this.wordConfidences.set(lower, { confidence: 0.5, wasModified: true });
      } else {
        // Word observed directly - increase confidence
        const currentConf = this.getConfidence(lower);
        if (currentConf < 1.0) {
          // Increase confidence (0.5 -> 0.75 -> 1.0)
          const newConf = Math.min(1.0, currentConf + 0.25);
          this.wordConfidences.set(lower, { confidence: newConf, wasModified: false });
        } else {
          // Already at max confidence
          this.wordConfidences.set(lower, { confidence: 1.0, wasModified: false });
        }
      }
    }
    
    // Decrease confidence for words not observed (but don't remove yet - smoothing)
    for (const [word, entry] of this.wordConfidences.entries()) {
      if (!currentWordsSet.has(word)) {
        // Word not observed - decrease confidence slightly
        const newConf = Math.max(0.0, entry.confidence - 0.1);
        if (newConf <= 0.0) {
          // Remove if confidence drops to 0
          this.wordConfidences.delete(word);
        } else {
          this.wordConfidences.set(word, { confidence: newConf, wasModified: entry.wasModified });
        }
      }
    }
  }
  
  /**
   * Check if we should discard a modified word in favor of a new observation.
   * Returns true if the modified word should be discarded.
   */
  shouldDiscardModifiedWord(modifiedWord, newWord) {
    const modifiedConf = this.getConfidence(modifiedWord);
    const wasModified = this.wasModified(modifiedWord);
    
    // If modified word has low confidence (0.5) and we have a new observation, discard it
    if (wasModified && modifiedConf <= 0.5) {
      // Check if new word is similar to modified word (might be the real word)
      const modifiedLower = modifiedWord.toLowerCase();
      const newLower = newWord.toLowerCase();
      
      // If they're similar (one letter difference), prefer the new observation
      if (Math.abs(modifiedLower.length - newLower.length) <= 1) {
        // Check if they're one letter off
        const shorter = modifiedLower.length < newLower.length ? modifiedLower : newLower;
        const longer = modifiedLower.length > newLower.length ? modifiedLower : newLower;
        
        for (let i = 0; i < longer.length; i++) {
          const candidate = longer.slice(0, i) + longer.slice(i + 1);
          if (candidate === shorter) {
            return true; // Discard modified word, use new observation
          }
        }
      }
    }
    
    return false;
  }
  
  /**
   * Get all words with their confidence scores.
   */
  getAllWords() {
    return Array.from(this.wordConfidences.entries()).map(([word, entry]) => ({
      word,
      confidence: entry.confidence,
      wasModified: entry.wasModified,
    }));
  }
}

/**
 * Fuse data: correct words and restore missing words/letters.
 * @param {object} payload - Current payload from vision package
 * @param {object} previousState - Previous state { words: string[], availableLetters: string }
 * @param {Set<string>} dictSet - Dictionary as a Set for fast lookup
 * @param {FreeListTracker} freeListTracker - Tracker for free list persistence
 * @param {WordConfidenceTracker} confidenceTracker - Tracker for word confidence scores
 * @returns {object} - Fused payload
 */
export function fuseData(payload, previousState, dictSet, freeListTracker, confidenceTracker, wordVisibilityTracker) {
  const { wordsPerPlayer, availableLetters } = normalizeGameData(payload);
  const previousWords = previousState?.words || [];
  const oldFreeList = freeListTracker ? freeListTracker.getOldFreeList() : (previousState?.availableLetters || '');
  
  // Record raw VLM call for free list tracking
  if (freeListTracker) {
    freeListTracker.recordRawCall(availableLetters);
  }
  
  // Get raw input words for tracking and comparison
  const rawInputWords = wordsPerPlayer.flat().map(w => w.toLowerCase().trim());
  
  // Record raw VLM call for word visibility tracking
  if (wordVisibilityTracker) {
    wordVisibilityTracker.recordRawCall(rawInputWords);
  }
  
  // Step 1: First pass - identify disappeared words before correction
  const currentWordsSet = new Set();
  for (const playerWords of wordsPerPlayer) {
    for (const word of playerWords) {
      currentWordsSet.add(word.toLowerCase().trim());
    }
  }
  
  const disappearedWords = previousWords.filter(prevWord => {
    const prevLower = prevWord.toLowerCase();
    return !currentWordsSet.has(prevLower);
  });
  
  // Step 2: Correct words in player lists (with disappeared words context)
  const correctedWordsPerPlayer = [];
  const allCorrectedWords = [];
  const modifiedWords = []; // Track which words were modified
  
  for (const playerWords of wordsPerPlayer) {
    const correctedPlayerWords = [];
    for (const word of playerWords) {
      // Handle short words (< 3 letters): try to add a letter first (more likely missing a letter)
      if (word.length < MIN_WORD_LENGTH) {
        // Try adding a letter to make it a real word
        const withAddedLetter = checkAddOneLetter(word.toLowerCase().trim(), oldFreeList, dictSet);
        if (withAddedLetter && withAddedLetter.length >= MIN_WORD_LENGTH) {
          // Successfully corrected by adding a letter
          correctedPlayerWords.push(withAddedLetter);
          allCorrectedWords.push(withAddedLetter);
          modifiedWords.push(withAddedLetter);
        }
        // If couldn't correct it, just skip it (don't add to free list - memoryless)
        continue;
      }
      
      const result = correctWord(word, previousWords, oldFreeList, dictSet, disappearedWords);
      const corrected = result.word;
      const wasModified = result.wasModified;
      
      if (Array.isArray(corrected)) {
        // Word was split into multiple words - filter to ensure each is at least MIN_WORD_LENGTH
        const validSplitWords = corrected.filter(w => w.length >= MIN_WORD_LENGTH);
        if (validSplitWords.length > 0) {
          correctedPlayerWords.push(...validSplitWords);
          allCorrectedWords.push(...validSplitWords);
          // All split words are considered modified
          modifiedWords.push(...validSplitWords);
        }
      } else {
        // Only add if word meets minimum length requirement
        if (corrected.length >= MIN_WORD_LENGTH) {
          correctedPlayerWords.push(corrected);
          allCorrectedWords.push(corrected);
          if (wasModified) {
            modifiedWords.push(corrected);
          }
        }
      }
    }
    correctedWordsPerPlayer.push(correctedPlayerWords);
  }
  
  // Step 2.5: Use confidence to filter out low-confidence modified words if we have better observations
  if (confidenceTracker) {
    const modifiedWordsSet = new Set(modifiedWords.map(w => w.toLowerCase()));
    const filteredWordsPerPlayer = [];
    const filteredAllWords = [];
    
    for (let i = 0; i < correctedWordsPerPlayer.length; i++) {
      const playerWords = correctedWordsPerPlayer[i];
      const filteredPlayerWords = [];
      
      for (const word of playerWords) {
        const lower = word.toLowerCase();
        const wasModified = modifiedWordsSet.has(lower);
        
        // Check if this modified word should be discarded
        if (wasModified && confidenceTracker.wasModified(lower)) {
          // Check if any new observation should replace this modified word
          let shouldDiscard = false;
          
          // First check using the confidence tracker's method
          for (const rawWord of rawInputWords) {
            if (rawWord !== lower && confidenceTracker.shouldDiscardModifiedWord(lower, rawWord)) {
              shouldDiscard = true;
              break;
            }
          }
          
          // Also check if a raw input word is similar (one letter off) and is a real word
          // This handles the case where we guessed "cart" from "cat", but now "cart" comes in correctly
          if (!shouldDiscard) {
            for (const rawWord of rawInputWords) {
              if (rawWord === lower) {
                // The real word is in the input - this means our correction was right, but we should
                // use the input version (which might have been corrected differently or is the real observation)
                // Actually, if rawWord === lower, they're the same, so no need to discard
                continue;
              }
              
              // Check if they're one letter off
              if (Math.abs(lower.length - rawWord.length) <= 1) {
                const shorter = lower.length < rawWord.length ? lower : rawWord;
                const longer = lower.length > rawWord.length ? lower : rawWord;
                
                // Check if removing one letter makes them match
                for (let j = 0; j < longer.length; j++) {
                  const candidate = longer.slice(0, j) + longer.slice(j + 1);
                  if (candidate === shorter) {
                    // They're one letter off - if the raw word is a real word, prefer it
                    if (isRealWord(rawWord, dictSet)) {
                      shouldDiscard = true; // Discard our modified guess, use the real word
                      break;
                    }
                  }
                }
                if (shouldDiscard) break;
              }
            }
          }
          
          if (!shouldDiscard) {
            filteredPlayerWords.push(word);
            filteredAllWords.push(word);
          }
          // If shouldDiscard is true, we skip this word (the real one will be added from raw input)
        } else {
          filteredPlayerWords.push(word);
          filteredAllWords.push(word);
        }
      }
      
      filteredWordsPerPlayer.push(filteredPlayerWords);
    }
    
    // Update corrected words with filtered results
    correctedWordsPerPlayer.length = 0;
    correctedWordsPerPlayer.push(...filteredWordsPerPlayer);
    allCorrectedWords.length = 0;
    allCorrectedWords.push(...filteredAllWords);
  }
  
  // Step 3: Check for disappeared words from previous state (after correction)
  const correctedWordsSet = new Set(allCorrectedWords.map(w => w.toLowerCase()));
  
  // Helper function to check if two words are similar (one letter off)
  function areWordsSimilar(word1, word2) {
    const w1 = word1.toLowerCase();
    const w2 = word2.toLowerCase();
    if (w1 === w2) return true; // Exact match
    if (Math.abs(w1.length - w2.length) > 1) return false;
    
    const shorter = w1.length < w2.length ? w1 : w2;
    const longer = w1.length > w2.length ? w1 : w2;
    
    // Check if removing one letter makes them match
    for (let i = 0; i < longer.length; i++) {
      const candidate = longer.slice(0, i) + longer.slice(i + 1);
      if (candidate === shorter) {
        return true;
      }
    }
    return false;
  }
  
  for (const prevWord of previousWords) {
    // Only restore words that meet minimum length requirement
    if (prevWord.length < MIN_WORD_LENGTH) continue;
    
    const prevLower = prevWord.toLowerCase();
    if (!correctedWordsSet.has(prevLower)) {
      // Check if it was recombined or has extra letters in corrected words
      let found = false;
      
      for (const correctedWord of allCorrectedWords) {
        const correctedLower = correctedWord.toLowerCase();
        // Check if previous word is contained in corrected word (with extra letters)
        if (correctedLower.includes(prevLower) || prevLower.includes(correctedLower)) {
          found = true;
          break;
        }
      }
      
      // IMPORTANT: Before restoring, check if any NEW word in the input is similar to it
      // If so, don't restore - the new similar word is probably the correct version
      if (!found) {
        let hasSimilarNewWord = false;
        for (const rawWord of rawInputWords) {
          if (areWordsSimilar(prevLower, rawWord)) {
            // There's a similar word in the new input - don't restore the old one
            hasSimilarNewWord = true;
            break;
          }
        }
        
        if (hasSimilarNewWord) {
          // Don't restore - similar word already exists in new input
          continue;
        }
      }
      
      if (!found) {
        // Word disappeared and wasn't found in any form, and no similar word in new input
        // Check if it appeared in the last 2 raw VLM calls - if not, don't restore (it's probably gone)
        if (wordVisibilityTracker && !wordVisibilityTracker.wasSeenInLastTwoCalls(prevLower)) {
          // Word hasn't appeared in last 2 calls - don't restore it, it's probably not there anymore
          continue;
        }
        
        // Add it back (already checked it's >= MIN_WORD_LENGTH and appeared in last 2 calls)
        if (correctedWordsPerPlayer.length > 0) {
          correctedWordsPerPlayer[0].push(prevWord);
          allCorrectedWords.push(prevWord);
        }
      }
    }
  }
  
  // Step 5: Free list - just pass through whatever VLM gives (memoryless)
  const finalFreeList = (availableLetters || '').toLowerCase();
  
  // Final filter: ensure all words meet minimum length requirement
  const finalWordsPerPlayer = correctedWordsPerPlayer.map(words => 
    words.filter(w => w.length >= MIN_WORD_LENGTH)
  );
  const finalAllWords = allCorrectedWords.filter(w => w.length >= MIN_WORD_LENGTH);
  
  // Update confidence tracker with final word list
  if (confidenceTracker) {
    const finalWords = finalAllWords.map(w => typeof w === 'string' ? w : w.join(''));
    const modifiedWordsLower = modifiedWords.filter(w => w.length >= MIN_WORD_LENGTH).map(w => w.toLowerCase());
    confidenceTracker.update(finalWords, modifiedWordsLower);
  }
  
  return {
    players: finalWordsPerPlayer.map(words => ({ words })),
    availableLetters: finalFreeList,
  };
}

export { FreeListTracker, WordConfidenceTracker, WordVisibilityTracker };

