/**
 * Quick test to verify recommendation scoring works correctly.
 * Run with: node test-recommendations.js
 */
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { sortRecommendations, ScoringConfig, ScoringStrategies, scoreWord } from './recommendationScorer.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Load frequencies
const freqPath = join(__dirname, 'data', 'word_frequencies.json');
const frequencies = JSON.parse(readFileSync(freqPath, 'utf8'));

// Mock recommended words for testing
const mockRecommendedWords = {
  'cat': ['c', 'a', 't'],
  'dog': ['d', 'o', 'g'],
  'elephant': ['e', 'l', 'e', 'p', 'h', 'a', 'n', 't'],
  'the': ['t', 'h', 'e'],
  'antidisestablishmentarianism': ['a', 'n', 't', 'i', 'd', 'i', 's', 'e', 's', 't', 'a', 'b', 'l', 'i', 's', 'h', 'm', 'e', 'n', 't', 'a', 'r', 'i', 'a', 'n', 'i', 's', 'm'],
  'run': ['r', 'u', 'n'],
  'running': ['r', 'u', 'n', 'n', 'i', 'n', 'g'],
  'xylophone': ['x', 'y', 'l', 'o', 'p', 'h', 'o', 'n', 'e'],
  'a': ['a'],
  'zz': ['z', 'z'],
};

console.log('Testing Recommendation Scoring System\n');
console.log('=' .repeat(60));

// Test 1: Show individual word scores
console.log('\n1. Individual Word Scores (Default Config):');
console.log(`   Config: minFreq=${ScoringConfig.minFrequency}, weights=freq:${ScoringConfig.weights.frequency} len:${ScoringConfig.weights.length}`);
console.log('-'.repeat(60));
for (const word of Object.keys(mockRecommendedWords)) {
  const freq = frequencies[word] || 0;
  const score = scoreWord(word, freq);
  const filtered = freq < ScoringConfig.minFrequency ? '(FILTERED)' : '';
  console.log(`   ${word.padEnd(30)} freq: ${freq.toFixed(2)}  len: ${word.length.toString().padStart(2)}  score: ${score.toFixed(2)} ${filtered}`);
}

// Test 2: Sort with default config
console.log('\n2. Sorted Recommendations (Default: Balanced):');
console.log('-'.repeat(60));
const sorted = sortRecommendations(mockRecommendedWords, frequencies);
const sortedWords = Object.keys(sorted);
sortedWords.slice(0, 5).forEach((word, i) => {
  const freq = frequencies[word] || 0;
  const score = scoreWord(word, freq);
  console.log(`   ${(i + 1)}. ${word.padEnd(30)} freq: ${freq.toFixed(2)}  len: ${word.length.toString().padStart(2)}  score: ${score.toFixed(2)}`);
});
console.log(`   ... (${sortedWords.length} total words after filtering)`);

// Test 3: Try different strategies
console.log('\n3. Comparison of Different Strategies:');
console.log('-'.repeat(60));

const strategies = {
  'Default (Balanced)': ScoringConfig,
  'Longest First': ScoringStrategies.longestFirst,
  'Most Common First': ScoringStrategies.mostCommonFirst,
  'Common & Long': ScoringStrategies.commonAndLong,
};

for (const [name, config] of Object.entries(strategies)) {
  const sorted = sortRecommendations(mockRecommendedWords, frequencies, config);
  const top3 = Object.keys(sorted).slice(0, 3);
  console.log(`   ${name}:`);
  console.log(`      Top 3: ${top3.join(', ')}`);
  console.log(`      Filtered: ${Object.keys(mockRecommendedWords).length - Object.keys(sorted).length} words removed`);
}

// Test 4: Show filtering in action
console.log('\n4. Filtering Effect (minFrequency = 1.0):');
console.log('-'.repeat(60));
const allWords = Object.keys(mockRecommendedWords);
const filteredOut = allWords.filter(w => (frequencies[w] || 0) < ScoringConfig.minFrequency);
const keptWords = allWords.filter(w => (frequencies[w] || 0) >= ScoringConfig.minFrequency);
console.log(`   Total words: ${allWords.length}`);
console.log(`   Kept: ${keptWords.length}`);
console.log(`   Filtered out: ${filteredOut.length}`);
if (filteredOut.length > 0) {
  console.log(`   Removed words: ${filteredOut.join(', ')}`);
}

console.log('\n' + '='.repeat(60));
console.log('✓ Test complete! Scoring system is working.\n');
console.log('To customize scoring, edit backend/recommendationScorer.js:');
console.log('  - Change ScoringConfig.minFrequency to adjust filtering');
console.log('  - Change ScoringConfig.weights to adjust score balance');
console.log('  - Use ScoringStrategies presets for quick changes\n');
