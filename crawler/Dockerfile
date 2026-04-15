FROM python:3.12-slim

WORKDIR /app

# System-Abhängigkeiten
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Dateien nach /app/crawler/ kopieren, damit "from crawler.xxx" imports funktionieren
COPY . ./crawler/

RUN mkdir -p output logs

ENV PYTHONPATH=/app

EXPOSE 8000

# PORT wird von Railway/Cloud-Plattformen gesetzt, fallback 8000
CMD ["sh", "-c", "uvicorn crawler.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
