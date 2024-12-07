FROM python:3.12-slim


COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /backend
WORKDIR /backend

RUN uv sync --frozen --no-cache

RUN uv pip install fastapi[standard]

# Run the application.
CMD [".venv/bin/fastapi", "run", "main.py", "--port", "8000", "--host", "0.0.0.0"]