# Multi-stage Dockerfile cho He thong RAG Quy dinh hoc vu
FROM python:3.12-slim

# Thiet lap moi truong
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PORT=8000

WORKDIR /app

# Cai dat cac dependency he thong toi thieu
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy va cai dat requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir sentence-transformers chromadb fastapi uvicorn openai pydantic python-dotenv

# Copy toan bo source code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Lenh khoi chay
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

