FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy DATA_DIR=/data
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY app ./app
COPY --from=frontend /build/dist ./frontend/dist
EXPOSE 8100
CMD ["/app/.venv/bin/uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8100"]
