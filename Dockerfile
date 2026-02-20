FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && pip install --no-cache-dir 'uv==0.10.3'

COPY --chown=appuser:appuser . /app

# Install runtime dependencies with uv lockfile fidelity.
USER appuser
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["sh", "-c", "python -c \"import urllib.request, os; u = urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=3); exit(0 if u.getcode() == 200 else 1)\" || exit 1"]

CMD ["sh", "-c", "uv run uvicorn simulation.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-*}\""]
