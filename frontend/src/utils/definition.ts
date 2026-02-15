/**
 * Fetches the definition of a word from the backend
 * @param word - The word to get the definition for
 * @returns The definition string, or null if not found or error
 */
export async function fetchDefinition(word: string): Promise<string | null> {
    try {
        const response = await fetch(`http://localhost:3000/definition/${word.toLowerCase()}`);
        const data = await response.json();
        if (data.ok && data.definition) {
            return data.definition;
        }
        return null;
    } catch (error) {
        console.error(`Error fetching definition for "${word}":`, error);
        return null;
    }
}

