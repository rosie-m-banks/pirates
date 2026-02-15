import { useEffect, useState } from "react";
import { io, Socket } from "socket.io-client";
import StudentView from "./StudentView";
import ValidationView from "./ValidationView";
import TeacherView from "./TeacherView";
import type { TeacherGameData } from "./types/stats";

type ViewMode = "student" | "validation" | "teacher";

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

const temporaryGameData: GameData = {
    players: [
        { words: ["app", "banana", "cherry"] },
        { words: ["dog", "cat", "bird"] },
    ],
    availableLetters: "le",
    recommendedWords: {
        apple: ["app", "l", "e"],
    },
};

function App() {
    const [gameData, setGameData] = useState<GameData | null>(
        temporaryGameData,
    );
    const [teacherGameData, setTeacherGameData] =
        useState<TeacherGameData | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    const viewMode: ViewMode = (() => {
        const params = new URLSearchParams(window.location.search);
        const view = params.get("view");
        if (view === "validation" || view === "teacher") return view;
        return "student";
    })();

    useEffect(() => {
        const titles: Record<ViewMode, string> = {
            student: "Pirates - Student",
            validation: "Pirates - Data",
            teacher: "Pirates - Teacher",
        };
        document.title = titles[viewMode];
    }, [viewMode]);

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

        function onGameState(data: any) {
            console.log("Received game state:", data);

            // Transform backend snake_case to frontend camelCase for basic views
            const transformedData: GameData = {
                players: data.players,
                availableLetters: data.availableLetters,
                recommendedWords: data.recommended_words,
            };
            setGameData(transformedData);

            // Store full data including move and analytics for teacher view
            const teacherData: TeacherGameData = {
                ...transformedData,
                move: data.move,
                _analytics: data._analytics,
            };
            setTeacherGameData(teacherData);
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
            <div className="min-h-screen flex flex-col items-center justify-start py-12 px-8">
                <header className="mb-8 flex items-center gap-6">
                    <img
                        src="/logo.png"
                        alt="Pirates logo"
                        className="w-30 h-30"
                    />
                    <h1
                        className="relative text-8xl tracking-wider flex items-center gap-4"
                        style={{
                            fontFamily: "FatPix, sans-serif",
                        }}
                    >
                        {/* Shadow layer */}
                        <span className="absolute top-2 left-2 text-black/60 select-none pointer-events-none">
                            Pirates
                        </span>

                        {/* Main text */}
                        <span
                            className="relative text-(--ocean-blue)"
                            style={{ WebkitTextStroke: "4px white" }}
                        >
                            Pirates
                        </span>
                    </h1>
                </header>

                {gameData && viewMode === "student" && (
                    <StudentView
                        availableLetters={gameData.availableLetters}
                        players={gameData.players}
                        recommendedWords={gameData.recommendedWords}
                    />
                )}
                {gameData && viewMode === "validation" && (
                    <ValidationView
                        availableLetters={gameData.availableLetters}
                        players={gameData.players}
                        recommendedWords={gameData.recommendedWords}
                    />
                )}
                {teacherGameData && viewMode === "teacher" && (
                    <TeacherView gameData={teacherGameData} />
                )}
                {!gameData && <div>Waiting for words...</div>}
            </div>
        </>
    );
}

export default App;
