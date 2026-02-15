/**
 * Backend server: Express HTTP API + Socket.IO for game state and image updates.
 * - POST /update-data  -> run anagram worker on game state, broadcast result to all WS clients.
 * - POST /update-image -> run image worker, broadcast to WS clients.
 * - WebSocket path /receive-data -> clients receive broadcasted 'data' events.
 */
import express from "express";
import { createServer } from "http";
import { Server } from "socket.io";
import { Worker } from "worker_threads";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import cors from "cors";
import { readFile } from "fs/promises";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));
app.use(express.raw({ type: "application/octet-stream", limit: "10mb" }));

const httpServer = createServer(app);

// Socket.IO on path /receive-data — clients connect at ws://host/receive-data and get 'data' events
const io = new Server(httpServer, {
    path: "/receive-data",
    cors: {
        origin: "*",
    },
});

/** Send a message to every connected WebSocket client. */
function broadcast(message) {
    io.emit("data", message);
}

const workerPath = join(__dirname, "worker.js");
let sharedWorker = null;
/** @type {{ kind: string, payload: unknown, resolve: (r: unknown) => void, reject: (e: Error) => void }[] */
const workerQueue = [];

function onWorkerMessage(msg) {
    const next = workerQueue.shift();
    if (next) {
        if (msg.ok) next.resolve(msg.result);
        else next.reject(new Error(msg.error));
    }
    const pending = workerQueue[0];
    if (pending) sharedWorker.postMessage({ kind: pending.kind, payload: pending.payload });
}

/**
 * Run worker with the given message kind and payload. Uses a single long-lived worker and a queue.
 * Resolves with worker result or rejects on error. Worker state (e.g. subset cache) is reused across requests.
 */
function runWorker(kind, payload) {
    return new Promise((resolve, reject) => {
        workerQueue.push({ kind, payload, resolve, reject });
        if (workerQueue.length === 1) {
            if (!sharedWorker) {
                sharedWorker = new Worker(workerPath, { workerData: {} });
                sharedWorker.on("message", onWorkerMessage);
                sharedWorker.on("error", (err) => {
                    const p = workerQueue.shift();
                    if (p) p.reject(err);
                    sharedWorker = null;
                });
            }
            sharedWorker.postMessage({ kind, payload });
        }
    });
}

io.on("connection", () => {
    // Clients connected on /receive-data; they receive via io.emit('data', ...)
});

// Load definitions file (lazy load, cached in memory)
let definitionsCache = null;
const definitionsPath = join(__dirname, "data", "definitions.json");

async function loadDefinitions() {
    if (definitionsCache === null) {
        try {
            const data = await readFile(definitionsPath, "utf-8");
            definitionsCache = JSON.parse(data);
            console.log(`Loaded ${Object.keys(definitionsCache).length} definitions`);
        } catch (err) {
            console.error("Failed to load definitions:", err.message);
            definitionsCache = {}; // Empty cache on error
        }
    }
    return definitionsCache;
}

// GET /definition/:word — get definition for a word
app.get("/definition/:word", async (req, res) => {
    try {
        const word = req.params.word.toLowerCase().trim();
        if (!word) {
            return res.status(400).json({ ok: false, error: "Word parameter required" });
        }
        
        const definitions = await loadDefinitions();
        const definition = definitions[word];
        
        if (definition) {
            res.json({ ok: true, word, definition });
        } else {
            res.json({ ok: true, word, definition: null });
        }
    } catch (err) {
        res.status(500).json({ ok: false, error: err.message });
    }
});

// POST /update-data — receive game state (JSON), process in worker, broadcast result to all WS clients
app.post("/update-data", async (req, res) => {
    try {
        const payload = req.body;
        const result = await runWorker("game-state", payload);
        broadcast(result);
        res.json({ ok: true, broadcast: io.engine.clientsCount });
    } catch (err) {
        res.status(500).json({ ok: false, error: err.message });
    }
});

// POST /update-image — accept JSON (metadata/base64) or raw binary; process in worker and broadcast
app.post("/update-image", async (req, res) => {
    try {
        const isJson = req.is("application/json");
        const payload = isJson
            ? req.body
            : {
                  binary: true,
                  length: req.body?.length ?? 0,
                  base64: req.body?.length
                      ? req.body.toString("base64")
                      : undefined,
              };
        if (
            isJson &&
            (!payload ||
                (typeof payload === "object" && !Object.keys(payload).length))
        ) {
            return res
                .status(400)
                .json({ ok: false, error: "Expected JSON body or image data" });
        }
        const result = await runWorker("image", payload);
        broadcast(result);
        res.json({ ok: true, broadcast: io.engine.clientsCount });
    } catch (err) {
        res.status(500).json({ ok: false, error: err.message });
    }
});

httpServer.listen(PORT, () => {
    console.log(`Server listening on http://localhost:${PORT}`);
    console.log(
        "  GET  /definition/:word - get definition for a word",
    );
    console.log(
        "  POST /update-data  - send game state (JSON), broadcast to /receive-data",
    );
    console.log(
        "  POST /update-image - send image update, broadcast to /receive-data",
    );
    console.log(
        "  WS   /receive-data - connect to receive broadcasted updates",
    );
});
