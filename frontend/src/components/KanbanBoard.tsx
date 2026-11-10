"use client";

import { useState, type FormEvent } from "react";
import clsx from "clsx";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, moveCard, type BoardData, type Card, type Column } from "@/lib/kanban";
import {
  fetchBoard,
  fetchChatHistory,
  saveBoard,
  sendChat,
  verifyCredentials,
  type ChatMessage,
  type Credentials,
} from "@/lib/api";

const defaultCredentials: Credentials = { username: "", password: "" };

export const KanbanBoard = () => {
  const [credentials, setCredentials] = useState<Credentials>(defaultCredentials);
  const [auth, setAuth] = useState<Credentials | null>(null);
  const [board, setBoard] = useState<BoardData | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);
  const [sendingChat, setSendingChat] = useState(false);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  // The board is locked while the AI is responding, because the AI reply replaces the whole board.
  const applyBoardUpdate = (updater: (prev: BoardData) => BoardData) => {
    if (!auth || !board || sendingChat) {
      return;
    }
    const next = updater(board);
    setBoard(next);
    saveBoard(auth, next)
      .then(() => setBoardError(null))
      .catch(async (error: Error) => {
        setBoardError(`${error.message} Reloaded the last saved board.`);
        setBoard(await fetchBoard(auth));
      });
  };

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoggingIn(true);
    setAuthError(null);
    try {
      const ok = await verifyCredentials(credentials);
      if (!ok) {
        setAuthError("Invalid credentials.");
        return;
      }
      const [remoteBoard, history] = await Promise.all([
        fetchBoard(credentials),
        fetchChatHistory(credentials),
      ]);
      setBoard(remoteBoard);
      setMessages(history);
      setBoardError(null);
      setChatError(null);
      setAuth(credentials);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Login failed.");
    } finally {
      setLoggingIn(false);
    }
  };

  const handleLogout = () => {
    setAuth(null);
    setCredentials(defaultCredentials);
    setMessages([]);
    setBoard(null);
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    if (!over || active.id === over.id) {
      return;
    }
    applyBoardUpdate((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    applyBoardUpdate((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddColumn = () => {
    const id = createId("col");
    applyBoardUpdate((prev) => ({
      ...prev,
      columns: [...prev.columns, { id, title: "New Column", cardIds: [] }],
    }));
  };

  const handleRemoveColumn = (columnId: string) => {
    applyBoardUpdate((prev) => {
      if (prev.columns.length <= 1) {
        return prev;
      }
      const columnToRemove = prev.columns.find((column) => column.id === columnId);
      if (!columnToRemove) {
        return prev;
      }
      const cards = { ...prev.cards };
      columnToRemove.cardIds.forEach((cardId) => {
        delete cards[cardId];
      });
      return {
        ...prev,
        cards,
        columns: prev.columns.filter((column) => column.id !== columnId),
      };
    });
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    applyBoardUpdate((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleEditCard = (cardId: string, title: string, details: string) => {
    applyBoardUpdate((prev) => ({
      ...prev,
      cards: { ...prev.cards, [cardId]: { id: cardId, title, details } },
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    applyBoardUpdate((prev) => ({
      ...prev,
      cards: Object.fromEntries(
        Object.entries(prev.cards).filter(([id]) => id !== cardId)
      ),
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
          : column
      ),
    }));
  };

  const handleSendChat = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!auth || !chatInput.trim()) {
      return;
    }
    const message = chatInput.trim();
    setSendingChat(true);
    setChatError(null);
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setChatInput("");
    try {
      const response = await sendChat(auth, message);
      setMessages((prev) => [...prev, { role: "assistant", content: response.message }]);
      if (response.board_updated && response.board) {
        setBoard(response.board);
      }
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Chat failed.");
    } finally {
      setSendingChat(false);
    }
  };

  if (!auth || !board) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md items-center px-6">
        <form
          onSubmit={handleLogin}
          className="w-full rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
            Project Management MVP
          </p>
          <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
            Sign in
          </h1>
          <p className="mt-2 text-sm text-[var(--gray-text)]">
            Use <strong>user</strong> / <strong>password</strong>.
          </p>

          <label className="mt-6 block text-sm font-semibold text-[var(--navy-dark)]">
            Username
            <input
              value={credentials.username}
              onChange={(event) =>
                setCredentials((prev) => ({ ...prev, username: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-[var(--stroke)] px-3 py-2 outline-none focus:border-[var(--primary-blue)]"
            />
          </label>
          <label className="mt-4 block text-sm font-semibold text-[var(--navy-dark)]">
            Password
            <input
              type="password"
              value={credentials.password}
              onChange={(event) =>
                setCredentials((prev) => ({ ...prev, password: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-[var(--stroke)] px-3 py-2 outline-none focus:border-[var(--primary-blue)]"
            />
          </label>
          {authError ? <p className="mt-4 text-sm text-red-600">{authError}</p> : null}
          <button
            type="submit"
            disabled={loggingIn}
            className="mt-6 w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            {loggingIn ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </main>
    );
  }

  const activeCard = activeCardId ? board.cards[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1600px] gap-6 px-6 pb-16 pt-12">
        <div className="flex-1">
          <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
            <div className="flex flex-wrap items-start justify-between gap-6">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                  Single Board Kanban
                </p>
                <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                  Kanban Studio
                </h1>
                <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                  Board changes are persisted by backend API. Add or remove columns as
                  needed, then collaborate with the AI assistant in the sidebar.
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleAddColumn}
                  type="button"
                  disabled={sendingChat}
                  className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] disabled:opacity-40"
                >
                  Add column
                </button>
                <button
                  onClick={handleLogout}
                  type="button"
                  className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white"
                >
                  Log out
                </button>
              </div>
            </div>
            {sendingChat ? (
              <p className="text-sm text-[var(--gray-text)]">
                The board is locked while the AI assistant is responding.
              </p>
            ) : null}
            {boardError ? <p className="text-sm text-red-600">{boardError}</p> : null}
          </header>

          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section
              aria-busy={sendingChat}
              data-testid="board"
              className={clsx(
                "mt-6 grid gap-6 md:grid-cols-2 xl:grid-cols-4",
                sendingChat && "pointer-events-none opacity-60"
              )}
            >
              {board.columns.map((column: Column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.reduce<Card[]>((acc, cardId) => {
                    const card = board.cards[cardId];
                    if (card) {
                      acc.push(card);
                    }
                    return acc;
                  }, [])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onEditCard={handleEditCard}
                  onDeleteCard={handleDeleteCard}
                  onRemoveColumn={handleRemoveColumn}
                  canRemove={board.columns.length > 1}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        </div>

        <aside className="w-full max-w-sm rounded-3xl border border-[var(--stroke)] bg-white p-5 shadow-[var(--shadow)]">
          <h2 className="font-display text-xl font-semibold text-[var(--navy-dark)]">
            AI Assistant
          </h2>
          <p className="mt-1 text-sm text-[var(--gray-text)]">
            Ask to create, edit, or move cards.
          </p>
          <div className="mt-4 h-[480px] overflow-y-auto rounded-2xl border border-[var(--stroke)] p-3">
            {messages.length === 0 ? (
              <p className="text-sm text-[var(--gray-text)]">
                Start a conversation and I will keep history for this user.
              </p>
            ) : (
              <div className="space-y-3">
                {messages.map((item, index) => (
                  <div
                    key={`${item.role}-${index}`}
                    className={`rounded-xl px-3 py-2 text-sm ${
                      item.role === "user"
                        ? "bg-[var(--primary-blue)] text-white"
                        : "bg-[var(--surface)] text-[var(--navy-dark)]"
                    }`}
                  >
                    <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide opacity-80">
                      {item.role}
                    </p>
                    <p>{item.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
          {chatError ? <p className="mt-2 text-sm text-red-600">{chatError}</p> : null}
          <form onSubmit={handleSendChat} className="mt-3 space-y-2">
            <textarea
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
              rows={4}
              placeholder="Tell AI what to update..."
              className="w-full resize-none rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
            />
            <button
              type="submit"
              disabled={sendingChat}
              className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {sendingChat ? "Sending..." : "Send"}
            </button>
          </form>
        </aside>
      </main>
    </div>
  );
};
