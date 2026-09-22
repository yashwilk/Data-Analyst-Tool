FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY start.sh ./start.sh
RUN chmod +x start.sh

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000 8501

CMD ["./start.sh"]
