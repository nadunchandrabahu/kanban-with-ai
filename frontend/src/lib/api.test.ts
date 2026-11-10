import {
  fetchBoard,
  fetchChatHistory,
  saveBoard,
  sendChat,
  verifyCredentials,
  type Credentials,
} from "@/lib/api";
import { sampleBoard } from "@/test/fixtures";

const credentials: Credentials = { username: "user", password: "password" };

const jsonResponse = (payload: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    })
  );

describe("api helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("verifies credentials", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse({ ok: true })));
    await expect(verifyCredentials(credentials)).resolves.toBe(true);
  });

  it("loads board and chat history", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => jsonResponse(sampleBoard))
      .mockImplementationOnce(() => jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchBoard(credentials)).resolves.toMatchObject(sampleBoard);
    await expect(fetchChatHistory(credentials)).resolves.toEqual([]);
  });

  it("saves board and sends chat", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => jsonResponse(sampleBoard))
      .mockImplementationOnce(() =>
        jsonResponse({ message: "Hi", board_updated: false, board: null })
      );
    vi.stubGlobal("fetch", fetchMock);
    await expect(saveBoard(credentials, sampleBoard)).resolves.toMatchObject(sampleBoard);
    await expect(sendChat(credentials, "hello")).resolves.toMatchObject({
      message: "Hi",
    });
  });

  it("throws on failed response", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse({ detail: "bad" }, 401)));
    await expect(fetchBoard(credentials)).rejects.toBeInstanceOf(Error);
  });
});
