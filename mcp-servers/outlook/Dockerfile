FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN mkdir -p /app/tokens && chmod 700 /app/tokens

EXPOSE 8002

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8002", "--log-level", "info"]
