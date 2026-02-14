/**
 * Backend server: Express HTTP API + Socket.IO for game state and image updates.
 * - POST /update-data  -> run anagram worker on game state, broadcast result to all WS clients.
 * - POST /update-image -> run image worker, broadcast to WS clients.
 * - WebSocket path /receive-data -> clients receive broadcasted 'data' events.
 */
import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import { Worker } from 'worker_threads';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;

const app = express();
app.use(express.json({ limit: '10mb' }));
app.use(express.raw({ type: 'application/octet-stream', limit: '10mb' }));

const httpServer = createServer(app);

// Socket.IO on path /receive-data — clients connect at ws://host/receive-data and get 'data' events
const io = new Server(httpServer, { path: '/receive-data' });

/** Send a message to every connected WebSocket client. */
function broadcast(message) {
  io.emit('data', message);
}

/**
 * Run worker.js with the given message kind and payload. Resolves with worker result or rejects on error.
 * Worker is terminated after one reply.
 */
function runWorker(kind, payload) {
  return new Promise((resolve, reject) => {
    const workerPath = join(__dirname, 'worker.js');
    const worker = new Worker(workerPath, { workerData: {} });
    worker.on('message', (msg) => {
      worker.terminate();
      if (msg.ok) resolve(msg.result);
      else reject(new Error(msg.error));
    });
    worker.on('error', (err) => {
      worker.terminate();
      reject(err);
    });
    worker.postMessage({ kind, payload });
  });
}

io.on('connection', () => {
  // Clients connected on /receive-data; they receive via io.emit('data', ...)
});

// POST /update-data — receive game state (JSON), process in worker, broadcast result to all WS clients
app.post('/update-data', async (req, res) => {
  try {
    const payload = req.body;
    const result = await runWorker('game-state', payload);
    broadcast(result);
    res.json({ ok: true, broadcast: io.engine.clientsCount });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /update-image — accept JSON (metadata/base64) or raw binary; process in worker and broadcast
app.post('/update-image', async (req, res) => {
  try {
    const isJson = req.is('application/json');
    const payload = isJson
      ? req.body
      : { binary: true, length: req.body?.length ?? 0, base64: req.body?.length ? req.body.toString('base64') : undefined };
    if (isJson && (!payload || (typeof payload === 'object' && !Object.keys(payload).length))) {
      return res.status(400).json({ ok: false, error: 'Expected JSON body or image data' });
    }
    const result = await runWorker('image', payload);
    broadcast(result);
    res.json({ ok: true, broadcast: io.engine.clientsCount });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

httpServer.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
  console.log('  POST /update-data  - send game state (JSON), broadcast to /receive-data');
  console.log('  POST /update-image - send image update, broadcast to /receive-data');
  console.log('  WS   /receive-data - connect to receive broadcasted updates');
});
