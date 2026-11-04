# Repository Guidelines

## Project Structure & Module Organization

`app/server.py` contains the FastAPI application, SQLite access, and the OpenAI-compatible model integration. `frontend/src/main.tsx` and `frontend/src/style.css` contain the React interface and its styling; Vite builds assets into `frontend/dist/`. API tests live in `tests/test_api.py`. `review/index.html` is the separate product discussion page served on port 8000. The application runs on port 8100. `Dockerfile` and `compose.yaml` define the NAS deployment.

## Build, Test, and Development Commands

- `uv sync`: install Python dependencies from `uv.lock`.
- `npm ci --prefix frontend`: install frontend dependencies from the lockfile.
- `npm run build --prefix frontend`: type-check and build the frontend for FastAPI to serve.
- `uv run uvicorn app.server:app --host 0.0.0.0 --port 8100`: run the application locally after building the frontend.
- `npm run dev --prefix frontend`: start the Vite development server; API requests proxy to port 8100.
- `uv run python -m pytest -q`: run backend tests.
- `docker compose up -d --build`: build and start the NAS deployment.

## Coding Style & Naming Conventions

Use four-space indentation and descriptive `snake_case` names in Python. Use TypeScript, React components, and `PascalCase` component names on the frontend; follow existing Ant Design patterns and keep shared styling in `frontend/src/style.css`. Prefer small, focused changes and typed API payloads. No dedicated formatter or linter is currently configured; the frontend build runs TypeScript checks.

## Testing Guidelines

Backend tests use pytest and FastAPI's `TestClient`. Name files `test_*.py` and test functions `test_*`. Use temporary databases and mock external model requests; never use household data or real API credentials in tests. Add tests for behavior changes, especially inventory and history transitions. No coverage threshold is currently configured.

## Commits & Pull Requests

There is no commit history yet, so no established commit convention can be inferred. Use concise, descriptive commit subjects. Pull requests should explain the behavior change, list validation performed, link relevant issues when available, and include screenshots for visible UI changes. Call out database or deployment changes explicitly.

## Security & Configuration

Copy `.env.example` to `.env` for model settings; never commit secrets. The app has no authentication and is intended for a trusted household network. Uploaded images are sent to the configured model provider. Preserve the SQLite data volume and test backups before migration or destructive operations.
