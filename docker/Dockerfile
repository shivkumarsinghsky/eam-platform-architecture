# Test runner image: domain, OpenAPI and SQL tests against the compose PostgreSQL.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[dev]"
COPY sql ./sql
COPY docs/api ./docs/api
COPY tests ./tests
RUN useradd --system --uid 10001 app
USER app
CMD ["pytest", "-v"]
