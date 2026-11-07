import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

const jsonResponse = (payload: unknown) =>
  Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })
  );

const setupFetchMock = () => {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.includes("/api/auth/verify") && method === "POST") {
      return jsonResponse({ ok: true });
    }
    if (url.includes("/api/board") && method === "GET") {
      return jsonResponse(initialData);
    }
    if (url.includes("/api/board") && method === "PUT") {
      return jsonResponse(JSON.parse(String(init?.body)));
    }
    if (url.includes("/api/chat/history")) {
      return jsonResponse([]);
    }
    if (url.includes("/api/chat") && method === "POST") {
      return jsonResponse({
        message: "AI reply",
        board_updated: false,
        board: null,
      });
    }
    return jsonResponse({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
};

const login = async () => {
  await userEvent.type(screen.getByLabelText(/username/i), "user");
  await userEvent.type(screen.getByLabelText(/password/i), "password");
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
};

describe("KanbanBoard", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders login by default", () => {
    render(<KanbanBoard />);
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
  });

  it("loads board after login", async () => {
    render(<KanbanBoard />);
    await login();
    expect(await screen.findByRole("heading", { name: /kanban studio/i })).toBeInTheDocument();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(4);
  });

  it("adds and removes a card in an authenticated board", async () => {
    render(<KanbanBoard />);
    await login();
    const column = screen.getAllByTestId(/column-/i)[0];
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "New card");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));
    expect(within(column).getByText("New card")).toBeInTheDocument();
    await userEvent.click(within(column).getByRole("button", { name: /delete new card/i }));
    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});
