/**
 * Tests for Pirates game state logic (gameState.js) and worker output format.
 * Run: npm test
 */
import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  processGameState,
  normalizeGameData,
  findOneConstruction,
  findFormableWords,
  letterCounts,
  MIN_WORD_LENGTH,
} from './gameState.js';

// Small deterministic dictionary for unit tests
const SMALL_DICT = ['act', 'cat', 'actor', 'car', 'at', 'cab', 'cart', 'tar', 'rat', 'or'];

describe('normalizeGameData', () => {
  it('accepts players with words', () => {
    const out = normalizeGameData({ players: [{ words: ['cat'] }], availableLetters: 'or' });
    assert.deepStrictEqual(out.wordsPerPlayer, [['cat']]);
    assert.strictEqual(out.availableLetters, 'or');
  });

  it('accepts wordsPerPlayer and available', () => {
    const out = normalizeGameData({ wordsPerPlayer: [['boat'], ['dog']], available: 'xyz' });
    assert.deepStrictEqual(out.wordsPerPlayer, [['boat'], ['dog']]);
    assert.strictEqual(out.availableLetters, 'xyz');
  });

  it('normalizes letters to lowercase and a-z only', () => {
    const out = normalizeGameData({ players: [], availableLetters: 'A-B 12' });
    assert.strictEqual(out.availableLetters, 'ab');
  });
});

describe('letterCounts and findFormableWords', () => {
  it('letterCounts returns counts', () => {
    assert.deepStrictEqual(letterCounts('aab'), { a: 2, b: 1 });
    assert.deepStrictEqual(letterCounts(''), {});
  });

  it('findFormableWords respects minLength', () => {
    const counts = letterCounts('abc');
    const found = findFormableWords(counts, SMALL_DICT, MIN_WORD_LENGTH);
    assert.ok(found.includes('cab'));
    assert.ok(!found.includes('at')); // length 2
  });
});

describe('findOneConstruction', () => {
  it('returns word + letters construction when valid', () => {
    const pool = letterCounts('cator'); // cat + or
    const construction = findOneConstruction('actor', ['cat'], pool);
    assert.ok(construction);
    assert.strictEqual(construction.length, 3); // cat, o, r
    assert.ok(construction.includes('cat'));
    assert.ok(construction.includes('o'));
    assert.ok(construction.includes('r'));
  });

  it('returns letters-only construction (≥2 blocks)', () => {
    const pool = letterCounts('cab');
    const construction = findOneConstruction('cab', [], pool);
    assert.ok(construction);
    assert.strictEqual(construction.length, 3);
    assert.deepStrictEqual([...construction].sort(), ['a', 'b', 'c']);
  });

  it('returns null for single-word anagram (no addition)', () => {
    const pool = letterCounts('cat'); // only word "cat", no extra letters
    const construction = findOneConstruction('act', ['cat'], pool);
    assert.strictEqual(construction, null);
  });

  it('uses full word when building (e.g. cat + r -> cart)', () => {
    const pool = letterCounts('catr');
    const construction = findOneConstruction('cart', ['cat'], pool);
    assert.ok(construction);
    assert.ok(construction.includes('cat'));
    assert.ok(construction.includes('r'));
  });
});

describe('processGameState output format', () => {
  it('returns players, recommended_words, availableLetters', () => {
    const result = processGameState(
      { players: [{ words: ['cat'] }], availableLetters: 'or' },
      SMALL_DICT
    );
    assert.ok('players' in result);
    assert.ok('recommended_words' in result);
    assert.ok('availableLetters' in result);
    assert.strictEqual(typeof result.availableLetters, 'string');
    assert.strictEqual(Array.isArray(result.players), true);
    assert.strictEqual(typeof result.recommended_words, 'object');
    assert.strictEqual(Array.isArray(result.recommended_words), false);
  });

  it('players echo input structure', () => {
    const result = processGameState(
      { players: [{ words: ['cat', 'dog'] }, { words: ['car'] }], availableLetters: '' },
      SMALL_DICT
    );
    assert.strictEqual(result.players.length, 2);
    assert.deepStrictEqual(result.players[0].words, ['cat', 'dog']);
    assert.deepStrictEqual(result.players[1].words, ['car']);
  });

  it('every recommended word has length >= 3', () => {
    const result = processGameState(
      { players: [], availableLetters: 'abcdefg' },
      ['ab', 'abc', 'abcd', 'cat', 'dog']
    );
    for (const word of Object.keys(result.recommended_words)) {
      assert.ok(word.length >= MIN_WORD_LENGTH, `word "${word}" should have length >= 3`);
    }
  });

  it('every construction has at least 2 blocks', () => {
    const result = processGameState(
      { players: [], availableLetters: 'abc' },
      ['cab', 'abc']
    );
    for (const [word, construction] of Object.entries(result.recommended_words)) {
      assert.ok(
        construction.length >= 2,
        `construction for "${word}" should have >= 2 blocks, got ${JSON.stringify(construction)}`
      );
    }
  });

  it('actor is recommended with cat + o + r when player has cat and letters or', () => {
    const result = processGameState(
      { players: [{ words: ['cat'] }], availableLetters: 'or' },
      SMALL_DICT
    );
    assert.ok('actor' in result.recommended_words);
    const construction = result.recommended_words['actor'];
    assert.ok(construction.includes('cat'));
    assert.ok(construction.includes('o'));
    assert.ok(construction.includes('r'));
  });

  it('act is NOT recommended when only cat is on board (anagram, no addition)', () => {
    const result = processGameState(
      { players: [{ words: ['cat'] }], availableLetters: '' },
      SMALL_DICT
    );
    assert.ok(!('act' in result.recommended_words));
  });

  it('availableLetters is echoed normalized', () => {
    const result = processGameState(
      { players: [], availableLetters: 'XyZ' },
      ['xyz']
    );
    assert.strictEqual(result.availableLetters, 'xyz');
  });
});

describe('worker integration (run worker with game-state)', () => {
  it('worker returns same shape: players, recommended_words, availableLetters', async () => {
    const { Worker } = await import('worker_threads');
    const { fileURLToPath } = await import('url');
    const { dirname, join } = await import('path');
    const __dirname = dirname(fileURLToPath(import.meta.url));
    const workerPath = join(__dirname, 'worker.js');

    const result = await new Promise((resolve, reject) => {
      const worker = new Worker(workerPath, { workerData: {} });
      worker.on('message', (msg) => {
        worker.terminate();
        if (msg.ok) resolve(msg.result);
        else reject(new Error(msg.error));
      });
      worker.on('error', reject);
      worker.postMessage({
        kind: 'game-state',
        payload: { players: [{ words: ['cat'] }], availableLetters: 'or' },
      });
    });

    assert.ok('players' in result);
    assert.ok('recommended_words' in result);
    assert.ok('availableLetters' in result);
    assert.strictEqual(result.availableLetters, 'or');
    assert.strictEqual(Array.isArray(result.players), true);
    assert.strictEqual(result.players.length, 1);
    assert.deepStrictEqual(result.players[0].words, ['cat']);
    // With full dictionary, "actor" should be in recommended_words
    assert.ok(
      typeof result.recommended_words === 'object' && !Array.isArray(result.recommended_words)
    );
  });
});
