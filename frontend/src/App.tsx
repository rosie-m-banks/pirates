import { useEffect, useState } from "react";
import { io, Socket } from "socket.io-client";
import StudentView from "./StudentView";

interface Player {
    words: string[];
}

interface GameData {
    players: Player[];
    recommended_words: Record<string, string[]>;
    availableLetters: string;
}

// Connect to backend WebSocket
const socket: Socket = io("http://localhost:3000", {
    path: "/receive-data",
    autoConnect: false,
});

function App() {
    const [gameData, setGameData] = useState<GameData | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        socket.connect();

        function onConnect() {
            setIsConnected(true);
            console.log("Connected to socket server");
        }

        function onDisconnect() {
            setIsConnected(false);
            console.log("Disconnected from socket server");
        }

        function onGameState(data: GameData) {
            console.log("Received game state:", data);
            setGameData(data);
        }

        socket.on("connect", onConnect);
        socket.on("disconnect", onDisconnect);
        socket.on("data", onGameState);

        return () => {
            socket.off("connect", onConnect);
            socket.off("disconnect", onDisconnect);
            socket.off("data", onGameState);
            socket.disconnect();
        };
    }, []);

    // Extract data for StudentView
    const availableLetters = gameData?.availableLetters
        ? gameData.availableLetters.toUpperCase().split("")
        : undefined;

    const playerWords =
        gameData?.players[0]?.words.map((w) => w.toUpperCase()) || undefined;

    const opponentWords =
        gameData?.players.slice(1).flatMap((p) => p.words) || undefined;

    // Generate hint from recommended words
    const hint =
        gameData && Object.keys(gameData.recommended_words).length > 0
            ? `Hint: You can make "${Object.keys(gameData.recommended_words)[0].toUpperCase()}" from ${gameData.recommended_words[Object.keys(gameData.recommended_words)[0]].map((w) => w.toUpperCase()).join(" + ")}`
            : undefined;

    return (
        <>
            <div
                style={{
                    position: "fixed",
                    top: "1rem",
                    right: "1rem",
                    padding: "0.5rem 1rem",
                    backgroundColor: isConnected ? "#10b981" : "#ef4444",
                    color: "white",
                    borderRadius: "0.5rem",
                    fontSize: "0.875rem",
                    fontWeight: "bold",
                    zIndex: 1000,
                }}
            >
                {isConnected ? "Connected" : "Disconnected"}
            </div>
            <StudentView
                availableLetters={availableLetters}
                playerWords={playerWords}
                opponentWords={opponentWords}
                hint={hint}
            />
        </>
    );
}

export default App;
