---
icon: lucide/rocket
---

# Get started

This runs the standalone application: the Flask backend plus the Vue
frontend, talking to each other over `/api/v1`.

## Prerequisites

- [Node.js](https://nodejs.org/) 22.18 or newer (Node 24.12+ is also
  supported) and npm
- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## 1. Install and start the backend

```bash
cd backend
uv sync
uv run flask --app vulniverse_api db upgrade
uv run flask --app vulniverse_api run --debug
```

The API listens on `http://127.0.0.1:5000` by default. The SQLite database
lives in the Flask instance directory (`backend/src/instance/`), created
automatically on first run.

## 2. Install and start the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. During development, Vite proxies `/api`
requests to the Flask server at `http://127.0.0.1:5000` (configured in
`frontend/vite.config.ts`) — the backend from step 1 must already be
running for the editor to load or save anything.

A stored record can be opened at `/editor/<record-id>`, for example
`/editor/CVE-2026-99999`.

## Development checks

```bash
# Frontend type-check and production build
cd frontend
npm run build

# Frontend lint (applies safe fixes)
npm run lint

# Backend tests
cd ../backend
uv run pytest

# Backend lint and type-check
uv run ruff check .
uv run mypy .
```

## Building the embeddable editor

To produce the self-contained `<vulniverse-editor>` Web Component instead
of (or in addition to) the standalone app:

```bash
cd frontend
npm run build:element
```

This writes a single file, `frontend/dist/element/vulniverse-editor.js`,
with its CSS and images inlined. See
[Architecture](../development/architecture.md) for what to do with it, and
[Embedding: Vulnerability-Lookup](../embedding/vl.md) for a worked example.

!!! warning

    `npm run build` (the standalone app) and `npm run build:element` share
    the same `frontend/dist/` output directory and both clear it on start.
    If you need both outputs, run `build:element` last — running the
    standalone build afterwards deletes the element bundle it just
    produced.
