import { useEffect, useState } from "react";
import { io, Socket } from "socket.io-client";
import StudentView from "./StudentView";

interface Player {
    words: string[];
}

// Backend data structure (snake_case from API)
interface BackendGameData {
    players: Player[];
    recommended_words: Record<string, string[]>;
    availableLetters: string;
}

// Frontend data structure (camelCase for consistency)
export interface GameData {
    players: Player[];
    recommendedWords: Record<string, string[]>;
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

        function onGameState(data: BackendGameData) {
            console.log("Received game state:", data);
            // Transform backend snake_case to frontend camelCase
            const transformedData: GameData = {
                players: data.players,
                availableLetters: data.availableLetters,
                recommendedWords: data.recommended_words,
            };
            setGameData(transformedData);
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
            {gameData && (
                <StudentView
                    availableLetters={gameData?.availableLetters}
                    players={gameData.players}
                    recommendedWords={gameData?.recommendedWords}
                />
            )}
        </>
    );
}

export default App;
