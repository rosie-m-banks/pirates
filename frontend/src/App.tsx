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

function App() {
    const [gameData, setGameData] = useState<GameData | null>(null);
    const [teacherGameData, setTeacherGameData] =
        useState<TeacherGameData | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [viewMode, setViewMode] = useState<ViewMode>("student");

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
                <header className="mb-8">
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

                {/* View Mode Toggle */}
                <div className="mb-8 flex gap-4">
                    <button
                        onClick={() => setViewMode("student")}
                        className="px-6 py-3 rounded-lg font-bold shadow-[4px_6px_0px_rgba(0,0,0)] transition-all"
                        style={{
                            backgroundColor:
                                viewMode === "student" ? "#6b9ac4" : "#e5e7eb",
                            color: viewMode === "student" ? "white" : "#6b7280",
                            border: `3px solid ${viewMode === "student" ? "#4e7ba8" : "#d1d5db"}`,
                            fontSize: "1.1rem",
                            transform:
                                viewMode === "student"
                                    ? "scale(1.05)"
                                    : "scale(1)",
                        }}
                    >
                        🎮 Student View
                    </button>
                    <button
                        onClick={() => setViewMode("validation")}
                        className="px-6 py-3 rounded-lg font-bold shadow-[4px_6px_0px_rgba(0,0,0)] transition-all"
                        style={{
                            backgroundColor:
                                viewMode === "validation"
                                    ? "#6b9ac4"
                                    : "#e5e7eb",
                            color:
                                viewMode === "validation" ? "white" : "#6b7280",
                            border: `3px solid ${viewMode === "validation" ? "#4e7ba8" : "#d1d5db"}`,
                            fontSize: "1.1rem",
                            transform:
                                viewMode === "validation"
                                    ? "scale(1.05)"
                                    : "scale(1)",
                        }}
                    >
                        ✅ Validation View
                    </button>
                    <button
                        onClick={() => setViewMode("teacher")}
                        className="px-6 py-3 rounded-lg font-bold shadow-[4px_6px_0px_rgba(0,0,0)] transition-all"
                        style={{
                            backgroundColor:
                                viewMode === "teacher" ? "#6b9ac4" : "#e5e7eb",
                            color: viewMode === "teacher" ? "white" : "#6b7280",
                            border: `3px solid ${viewMode === "teacher" ? "#4e7ba8" : "#d1d5db"}`,
                            fontSize: "1.1rem",
                            transform:
                                viewMode === "teacher"
                                    ? "scale(1.05)"
                                    : "scale(1)",
                        }}
                    >
                        👨‍🏫 Teacher View
                    </button>
                </div>

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
