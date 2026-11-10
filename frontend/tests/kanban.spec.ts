import { expect, test, type Page } from "@playwright/test";

const board = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-progress", title: "In Progress", cardIds: ["card-3"] },
    { id: "col-review", title: "Review", cardIds: ["card-4"] },
    { id: "col-done", title: "Done", cardIds: ["card-5"] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "A", details: "a" },
    "card-2": { id: "card-2", title: "B", details: "b" },
    "card-3": { id: "card-3", title: "C", details: "c" },
    "card-4": { id: "card-4", title: "D", details: "d" },
    "card-5": { id: "card-5", title: "E", details: "e" },
  },
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async (route, request) => {
    const url = request.url();
    if (url.endsWith("/api/auth/verify")) {
      await route.fulfill({ json: { ok: true } });
      return;
    }
    if (url.endsWith("/api/board") && request.method() === "GET") {
      await route.fulfill({ json: board });
      return;
    }
    if (url.endsWith("/api/board") && request.method() === "PUT") {
      await route.fulfill({
        body: request.postData() ?? "{}",
        contentType: "application/json",
      });
      return;
    }
    if (url.endsWith("/api/chat/history")) {
      await route.fulfill({ json: [] });
      return;
    }
    if (url.endsWith("/api/chat")) {
      await route.fulfill({
        json: { message: "AI reply", board_updated: false, board: null },
      });
      return;
    }
    await route.fulfill({ json: {} });
  });
});

async function login(page: Page) {
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("loads the kanban board", async ({ page }) => {
  await page.goto("/");
  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(4);
});

test("adds a card to a column", async ({ page }) => {
  await page.goto("/");
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await page.goto("/");
  await login(page);
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(columnBox.x + columnBox.width / 2, columnBox.y + 120, {
    steps: 12,
  });
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});

test("edits a card and renames a column", async ({ page }) => {
  const puts: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "PUT") {
      puts.push(request.postData() ?? "");
    }
  });
  await page.goto("/");
  await login(page);
  const card = page.getByTestId("card-card-1");
  await card.getByRole("button", { name: "Edit A" }).click();
  await card.getByLabel("Edit card title").fill("Edited in e2e");
  await card.getByRole("button", { name: "Save" }).click();
  await expect(card.getByText("Edited in e2e")).toBeVisible();

  const title = page.getByTestId("column-col-backlog").getByLabel("Column title");
  await title.fill("Renamed");
  await title.press("Enter");
  await expect(title).toHaveValue("Renamed");
  await expect.poll(() => puts.length).toBe(2);
  expect(JSON.parse(puts[1]).columns[0].title).toBe("Renamed");
});
