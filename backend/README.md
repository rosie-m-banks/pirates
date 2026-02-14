# Pirates — Backend

Backend for **Pirates**, a tile word game. Provides an HTTP API and WebSocket relay for game state (recommended words and constructions) and optional image updates. Word logic runs in a worker thread using a large dictionary.

## Quick start

```bash
npm install
npm start
```

Server runs at `http://localhost:3000` (or `PORT` env). For development with auto-restart:

```bash
npm run dev
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/update-data` | Send game state (JSON). Worker computes recommended words and constructions, then result is broadcast to all WebSocket clients. |
| POST | `/update-image` | Send image metadata or binary; result is broadcast to WebSocket clients. |
| WebSocket | `/receive-data` | Connect to receive broadcasted `data` events (game state or image results). |

### POST /update-data

**Request body** (JSON):

```json
{
  "players": [
    { "words": ["cat", "boat"] },
    { "words": ["dog"] }
  ],
  "availableLetters": "abcfg"
}
```

- `players`: array of `{ words: string[] }` — each player’s words on the board.
- `availableLetters`: string (or array of characters) — loose letters available to play.

Alternative shape: `wordsPerPlayer` (array of word arrays) and `available` instead of `availableLetters`.

**Broadcast response** (what clients receive on the `data` event):

```json
{
  "players": [
    { "words": ["cat", "boat"] },
    { "words": ["dog"] }
  ],
  "recommended_words": {
    "actor": ["cat", "o", "r"],
    "cab": ["c", "a", "b"]
  },
  "lettersToSteal": {
    "actor": 2,
    "cab": 3
  },
  "availableLetters": "abcfg"
}
```

- `players`: echo of input players/words.
- `recommended_words`: every valid word (length ≥ 3) that can be built by **adding** full words and/or letters, with one construction per word (each construction is a list of building blocks: player words or single letters).
- `lettersToSteal`: for each recommended word, how many letters you need to add (from your available letters) to form it — i.e. the number of single-letter blocks in the construction. Lower = easier to “steal”.
- `availableLetters`: normalized (lowercase, a-z only).

### Game rules (constructions)

- Only words that can be built by **adding** things count: e.g. `CAT + O + R → ACTOR` is valid; using only `CAT` to form `ACT` (anagram, no addition) is not.
- Every recommended word has length **≥ 3**.
- If a player word is used in a construction, **all** of its letters are used (no partial words).
- **Letters not from whole words** must come only from **available letters** (loose tiles). The backend never splits existing words into single letters — e.g. with words `cat`, `boat` and available `or`, `aboard` is not recommended (it would require using a, a, b, d from the words as loose letters).
- Each construction has at least **2** building blocks (e.g. word + letter, or several letters).

## Project layout

| File | Role |
|------|------|
| `server.js` | Express + Socket.IO; POST handlers and broadcast. |
| `worker.js` | Worker thread: loads dictionary, runs game-state logic, handles image updates. |
| `gameState.js` | Pure game logic: normalize payload, find formable words, build constructions. |
| `data/words.txt` | Dictionary (one word per line, a-z). Fallback list used if missing. |
| `worker.test.js` | Tests for `gameState.js` and worker output shape. |

## Tests

```bash
npm test
```

Uses Node’s built-in test runner. Covers input normalization, construction rules (word+letters, letters-only, no single-word anagram), output shape, and one worker integration test.
