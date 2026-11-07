# Database design (MVP)

The MVP uses SQLite with one board per user, stored as JSON for simplicity.

## Tables

### `users`

- `id` INTEGER PRIMARY KEY
- `username` TEXT UNIQUE NOT NULL
- `password` TEXT NOT NULL

Seeded user:

- `user` / `password`

### `boards`

- `user_id` INTEGER PRIMARY KEY (FK -> `users.id`)
- `data` TEXT NOT NULL (JSON board payload)
- `updated_at` TEXT NOT NULL (ISO-8601 UTC timestamp)

The board JSON shape:

- `columns`: ordered array of `{ id, title, cardIds[] }`
- `cards`: map of card id to `{ id, title, details }`

### `chat_messages`

- `id` INTEGER PRIMARY KEY
- `user_id` INTEGER NOT NULL (FK -> `users.id`)
- `role` TEXT NOT NULL (`user` or `assistant`)
- `content` TEXT NOT NULL
- `created_at` TEXT NOT NULL (ISO-8601 UTC timestamp)

## Why JSON for board data

For this MVP, board-as-JSON keeps writes simple and makes AI context transfer direct. The backend validates structure with pydantic on read/write to avoid malformed data drift.
