import type { BoardData } from "@/lib/kanban";

export type Credentials = {
  username: string;
  password: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatResponse = {
  message: string;
  board_updated: boolean;
  board: BoardData | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

const buildHeaders = (credentials: Credentials) => ({
  "Content-Type": "application/json",
  "x-username": credentials.username,
  "x-password": credentials.password,
});

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed.");
  }
  return (await response.json()) as T;
}

export async function verifyCredentials(credentials: Credentials): Promise<boolean> {
  const response = await fetch(`${API_BASE}/api/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
  const payload = await parseJson<{ ok: boolean }>(response);
  return payload.ok;
}

export async function fetchBoard(credentials: Credentials): Promise<BoardData> {
  const response = await fetch(`${API_BASE}/api/board`, {
    headers: buildHeaders(credentials),
  });
  return parseJson<BoardData>(response);
}

export async function saveBoard(
  credentials: Credentials,
  board: BoardData
): Promise<BoardData> {
  const response = await fetch(`${API_BASE}/api/board`, {
    method: "PUT",
    headers: buildHeaders(credentials),
    body: JSON.stringify(board),
  });
  return parseJson<BoardData>(response);
}

export async function fetchChatHistory(
  credentials: Credentials
): Promise<ChatMessage[]> {
  const response = await fetch(`${API_BASE}/api/chat/history`, {
    headers: buildHeaders(credentials),
  });
  return parseJson<ChatMessage[]>(response);
}

export async function sendChat(
  credentials: Credentials,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: buildHeaders(credentials),
    body: JSON.stringify({ message }),
  });
  return parseJson<ChatResponse>(response);
}
