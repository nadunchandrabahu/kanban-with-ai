# Frontend Overview

This frontend is a NextJS app router project focused on a single Kanban workspace.

## Structure

- `src/app/` contains the page shell and global styling.
- `src/components/` contains Kanban UI building blocks.
- `src/lib/kanban.ts` contains board types and helper functions.
- `tests/` contains Playwright integration coverage.
- `src/**/*.test.tsx` and `src/**/*.test.ts` contain unit tests with Vitest.

## Existing interaction model

- Board columns and cards render from in-memory data.
- Users can rename columns, add/delete cards, and drag cards between columns.
- DnD behavior is powered by `@dnd-kit`.

## Current testing stack

- Unit/integration style component and utility tests via Vitest + Testing Library.
- Browser-level tests via Playwright.
