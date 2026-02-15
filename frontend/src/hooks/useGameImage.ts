import { useState, useEffect } from "react";
import { io, Socket } from "socket.io-client";

interface ImageData {
    type: string;
    timestamp: number;
    data: {
        base64?: string;
        binary?: boolean;
        length?: number;
    };
    processed: boolean;
}

interface UseGameImageReturn {
    imageUrl: string | null;
    timestamp: number | null;
    isConnected: boolean;
}

/**
 * Hook to receive game board images via WebSocket
 * Listens to the dedicated 'image' event
 */
export function useGameImage(): UseGameImageReturn {
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [timestamp, setTimestamp] = useState<number | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const socket: Socket = io("http://localhost:3000", {
            path: "/receive-data",
        });

        socket.on("connect", () => {
            console.log("Connected to image WebSocket");
            setIsConnected(true);
        });

        socket.on("image", (imageData: ImageData) => {
            if (imageData.data?.base64) {
                // Convert base64 to data URL for display
                const dataUrl = `data:image/jpeg;base64,${imageData.data.base64}`;
                setImageUrl(dataUrl);
                setTimestamp(imageData.timestamp);
            }
        });

        socket.on("disconnect", () => {
            console.log("Disconnected from image WebSocket");
            setIsConnected(false);
        });

        socket.on("error", (err) => {
            console.error("Image WebSocket error:", err);
        });

        return () => {
            socket.disconnect();
        };
    }, []);

    return {
        imageUrl,
        timestamp,
        isConnected,
    };
}
