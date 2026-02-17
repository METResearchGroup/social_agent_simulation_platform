FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY . /app

# Install runtime dependencies with uv lockfile fidelity.
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn simulation.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
