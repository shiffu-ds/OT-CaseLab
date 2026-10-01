FROM python:3.12.14-slim-bookworm AS runtime
ARG INSTALL_NEURAL=false
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy PATH=/app/.venv/bin:$PATH
WORKDIR /app
RUN pip install --no-cache-dir uv==0.10.8 && groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
COPY pyproject.toml uv.lock /app/
RUN if [ "$INSTALL_NEURAL" = "true" ]; then apt-get update && apt-get install -y --no-install-recommends libcairo2 && rm -rf /var/lib/apt/lists/* && uv sync --frozen --no-dev --extra neural; else uv sync --frozen --no-dev; fi
COPY services /app/services
COPY scripts /app/scripts
COPY ai /app/ai
COPY ml /app/ml
COPY data/demo /app/data/demo
COPY alembic.ini /app/alembic.ini
RUN mkdir -p /app/.runtime/uploads /app/.runtime/models && chown -R app:app /app/.runtime
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
