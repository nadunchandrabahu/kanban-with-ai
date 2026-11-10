import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import type { BoardData } from "@/lib/kanban";
import { sampleBoard } from "@/test/fixtures";

const jsonResponse = (payload: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    })
  );

type Overrides = Partial<{
  verify: () => Promise<Response>;
  history: () => Promise<Response>;
  put: (body: BoardData) => Promise<Response>;
  chat: () => Promise<Response>;
}>;

const setupFetchMock = (overrides: Overrides = {}) => {
  let serverBoard: BoardData = structuredClone(sampleBoard);
  const puts: BoardData[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/auth/verify")) {
      return overrides.verify ? overrides.verify() : jsonResponse({ ok: true });
    }
    if (url.endsWith("/api/board") && method === "GET") {
      return jsonResponse(serverBoard);
    }
    if (url.endsWith("/api/board") && method === "PUT") {
      const body = JSON.parse(String(init?.body)) as BoardData;
      puts.push(body);
      if (overrides.put) {
        return overrides.put(body);
      }
      serverBoard = body;
      return jsonResponse(body);
    }
    if (url.endsWith("/api/chat/history")) {
      return overrides.history ? overrides.history() : jsonResponse([]);
    }
    if (url.endsWith("/api/chat")) {
      return overrides.chat
        ? overrides.chat()
        : jsonResponse({ message: "AI reply", board_updated: false, board: null });
    }
    throw new Error(`Unexpected request ${method} ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { puts };
};

const login = async () => {
  await userEvent.type(screen.getByLabelText(/username/i), "user");
  await userEvent.type(screen.getByLabelText(/password/i), "password");
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
};

const renderAndLogin = async () => {
  render(<KanbanBoard />);
  await login();
  await screen.findByRole("heading", { name: /kanban studio/i });
};

const firstColumn = () => screen.getAllByTestId(/^column-/)[0];

describe("KanbanBoard", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders login by default", () => {
    setupFetchMock();
    render(<KanbanBoard />);
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
  });

  it("loads the server board after login", async () => {
    setupFetchMock();
    await renderAndLogin();
    expect(screen.getAllByTestId(/^column-/)).toHaveLength(4);
    expect(screen.getByText("Align roadmap themes")).toBeInTheDocument();
  });

  it("shows an error and stays on login for invalid credentials", async () => {
    setupFetchMock({ verify: () => jsonResponse({ ok: false }) });
    render(<KanbanBoard />);
    await login();
    expect(await screen.findByText("Invalid credentials.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /kanban studio/i })).not.toBeInTheDocument();
  });

  it("stays on login with an error when loading data fails, and never saves", async () => {
    const { puts } = setupFetchMock({
      history: () => Promise.resolve(new Response("History unavailable", { status: 500 })),
    });
    render(<KanbanBoard />);
    await login();
    expect(await screen.findByText("History unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /kanban studio/i })).not.toBeInTheDocument();
    expect(screen.queryAllByTestId(/^column-/)).toHaveLength(0);
    expect(puts).toHaveLength(0);
  });

  it("adds and removes a card", async () => {
    setupFetchMock();
    await renderAndLogin();
    const column = firstColumn();
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "New card");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));
    expect(within(column).getByText("New card")).toBeInTheDocument();
    await userEvent.click(within(column).getByRole("button", { name: /delete new card/i }));
    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("edits a card title and details and saves them", async () => {
    const { puts } = setupFetchMock();
    await renderAndLogin();
    await userEvent.click(screen.getByRole("button", { name: "Edit Align roadmap themes" }));
    const title = screen.getByLabelText("Edit card title");
    const details = screen.getByLabelText("Edit card details");
    await userEvent.clear(title);
    await userEvent.type(title, "Edited title");
    await userEvent.clear(details);
    await userEvent.type(details, "Edited details");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Edited title")).toBeInTheDocument();
    expect(screen.getByText("Edited details")).toBeInTheDocument();
    expect(puts).toHaveLength(1);
    expect(puts[0].cards["card-1"]).toEqual({
      id: "card-1",
      title: "Edited title",
      details: "Edited details",
    });
  });

  it("cancelling a card edit saves nothing", async () => {
    const { puts } = setupFetchMock();
    await renderAndLogin();
    await userEvent.click(screen.getByRole("button", { name: "Edit Align roadmap themes" }));
    await userEvent.type(screen.getByLabelText("Edit card title"), " changed");
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByText("Align roadmap themes")).toBeInTheDocument();
    expect(puts).toHaveLength(0);
  });

  it("renames a column once, on blur, not on every keystroke", async () => {
    const { puts } = setupFetchMock();
    await renderAndLogin();
    const input = within(firstColumn()).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "Ideas");
    expect(puts).toHaveLength(0);
    await userEvent.tab();
    expect(puts).toHaveLength(1);
    expect(puts[0].columns[0].title).toBe("Ideas");
  });

  it("renames a column on Enter", async () => {
    const { puts } = setupFetchMock();
    await renderAndLogin();
    const input = within(firstColumn()).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "Ideas{Enter}");
    expect(puts).toHaveLength(1);
    expect(within(firstColumn()).getByLabelText("Column title")).toHaveValue("Ideas");
  });

  it("lets a column title be cleared while typing and reverts if left empty", async () => {
    const { puts } = setupFetchMock();
    await renderAndLogin();
    const input = within(firstColumn()).getByLabelText("Column title");
    await userEvent.clear(input);
    expect(input).toHaveValue("");
    await userEvent.tab();
    expect(input).toHaveValue("Backlog");
    expect(puts).toHaveLength(0);
  });

  it("adds and removes a column", async () => {
    const { puts } = setupFetchMock();
    await renderAndLogin();
    await userEvent.click(screen.getByRole("button", { name: /add column/i }));
    expect(screen.getAllByTestId(/^column-/)).toHaveLength(5);
    const newColumn = screen.getAllByTestId(/^column-/)[4];
    await userEvent.click(within(newColumn).getByRole("button", { name: "Remove" }));
    expect(screen.getAllByTestId(/^column-/)).toHaveLength(4);
    expect(puts).toHaveLength(2);
  });

  it("sends exactly one save per edit under StrictMode", async () => {
    const { puts } = setupFetchMock();
    render(
      <StrictMode>
        <KanbanBoard />
      </StrictMode>
    );
    await login();
    await screen.findByRole("heading", { name: /kanban studio/i });
    await userEvent.click(screen.getByRole("button", { name: /add column/i }));
    await waitFor(() => expect(puts).toHaveLength(1));
  });

  it("shows the error and reloads the saved board when a save fails", async () => {
    setupFetchMock({
      put: () => Promise.resolve(new Response("Save failed.", { status: 500 })),
    });
    await renderAndLogin();
    await userEvent.click(screen.getByRole("button", { name: /add column/i }));
    expect(await screen.findByText(/Save failed\. Reloaded the last saved board\./)).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByTestId(/^column-/)).toHaveLength(4));
  });

  it("sends a chat message, renders the reply and applies the board update", async () => {
    const updated: BoardData = {
      columns: [{ id: "col-ai", title: "AI column", cardIds: ["card-ai"] }],
      cards: { "card-ai": { id: "card-ai", title: "AI card", details: "" } },
    };
    setupFetchMock({
      chat: () => jsonResponse({ message: "Board updated.", board_updated: true, board: updated }),
    });
    await renderAndLogin();
    await userEvent.type(screen.getByPlaceholderText(/tell ai/i), "Replace the board");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Board updated.")).toBeInTheDocument();
    expect(screen.getByText("Replace the board")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^column-/)).toHaveLength(1);
    expect(screen.getByText("AI card")).toBeInTheDocument();
  });

  it("shows chat errors", async () => {
    setupFetchMock({
      chat: () => Promise.resolve(new Response("AI unavailable", { status: 502 })),
    });
    await renderAndLogin();
    await userEvent.type(screen.getByPlaceholderText(/tell ai/i), "hello");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("AI unavailable")).toBeInTheDocument();
  });

  it("locks the board while the AI is responding", async () => {
    let resolveChat: (response: Response) => void = () => {};
    const { puts } = setupFetchMock({
      chat: () => new Promise<Response>((resolve) => (resolveChat = resolve)),
    });
    await renderAndLogin();
    await userEvent.type(screen.getByPlaceholderText(/tell ai/i), "hello");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByTestId("board")).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText(/board is locked/i)).toBeInTheDocument();
    const addColumn = screen.getByRole("button", { name: /add column/i });
    expect(addColumn).toBeDisabled();
    fireEvent.click(within(firstColumn()).getByRole("button", { name: "Delete Align roadmap themes" }));
    expect(screen.getByText("Align roadmap themes")).toBeInTheDocument();
    expect(puts).toHaveLength(0);

    resolveChat(
      new Response(JSON.stringify({ message: "Done", board_updated: false, board: null }), {
        status: 200,
      })
    );
    expect(await screen.findByText("Done")).toBeInTheDocument();
    expect(screen.getByTestId("board")).toHaveAttribute("aria-busy", "false");
    expect(addColumn).toBeEnabled();
  });

  it("logs out back to the login screen", async () => {
    setupFetchMock();
    await renderAndLogin();
    await userEvent.click(screen.getByRole("button", { name: /log out/i }));
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
  });
});
