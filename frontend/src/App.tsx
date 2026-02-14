import { useEffect, useState } from "react";
import { io, Socket } from "socket.io-client";
import "./App.css";

// Define the data structure based on user request
interface Player {
    words: string[];
}

interface GameData {
    players: Player[];
    recommended_words: Record<string, string[]>;
    availableLetters: string;
}

// Ensure socket is initialized outside the component or memoized
// Replace with your actual backend URL
const socket: Socket = io("http://localhost:3000", {
    path: "/receive-data",
    autoConnect: false, // Prevent auto-connection for better control
});

// Fake test data for UI testing
const testGameData: GameData = {
    players: [
        {
            words: ["apple", "banana", "cherry"],
        },
        {
            words: ["grape", "melon"],
        },
    ],
    availableLetters: "abcdefg",
    recommended_words: {
        apple: ["app", "l", "e"],
        banana: ["nab", "a", "n", "a"],
    },
};

function App() {
    const [gameData, setGameData] = useState<GameData | null>(testGameData);
    const [isConnected, setIsConnected] = useState(socket.connected);

    useEffect(() => {
        // Connect to the socket server
        socket.connect();

        function onConnect() {
            setIsConnected(true);
            console.log("Connected to socket server");
        }

        function onDisconnect() {
            setIsConnected(false);
            console.log("Disconnected from socket server");
        }

        // Event listener for the specific data format
        function onGameState(data: GameData) {
            console.log("Received game state:", data);
            setGameData(data);
        }

        socket.on("connect", onConnect);
        socket.on("disconnect", onDisconnect);
        socket.on("data", onGameState); // Listening for 'data' event from backend

        // Cleanup on unmount
        return () => {
            socket.off("connect", onConnect);
            socket.off("disconnect", onDisconnect);
            socket.off("data", onGameState);
            socket.disconnect();
        };
    }, []);

    return (
        <div className="w-full h-full flex flex-col items-center justify-center p-4">
            <h1 className="text-2xl font-bold mb-4">Pirates Analysis</h1>

            <div className="mb-4">
                Status:{" "}
                <span
                    className={isConnected ? "text-green-500" : "text-red-500"}
                >
                    {isConnected ? "Connected" : "Disconnected"}
                </span>
            </div>

            {gameData ? (
                <div className="border p-4 rounded shadow-md w-full max-w-2xl bg-gray-50">
                    <h2 className="text-xl font-semibold mb-2">
                        Game Data Received:
                    </h2>

                    <div className="mb-4">
                        <h3 className="font-bold">Available Letters:</h3>
                        <p className="text-lg tracking-widest">
                            {gameData.availableLetters}
                        </p>
                    </div>

                    <div className="mb-4">
                        <h3 className="font-bold">Recommended Words</h3>
                        <ul className="list-disc pl-5 mt-1">
                            {Object.entries(gameData.recommended_words).map(
                                ([word, construction]) => (
                                    <li key={word}>
                                        <span className="font-bold">
                                            {word}
                                        </span>
                                        : {construction.join(", ")}
                                    </li>
                                ),
                            )}
                        </ul>
                    </div>

                    <div>
                        <h3 className="font-bold mb-2">Players:</h3>
                        {gameData.players.map((player, index) => (
                            <div
                                key={index}
                                className="mb-4 p-3 border rounded bg-white"
                            >
                                <h4 className="font-semibold">
                                    Player {index + 1}
                                </h4>

                                <div className="mt-2">
                                    <span className="font-medium">Words: </span>
                                    <span>{player.words.join(", ")}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                <p className="text-gray-500">Waiting for game data...</p>
            )}
        </div>
    );
}

export default App;
