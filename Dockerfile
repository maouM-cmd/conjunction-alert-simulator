FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY samples/ samples/
COPY alembic/ alembic/
COPY alembic.ini .

RUN mkdir -p data/cache

ENV PYTHONUNBUFFERED=1
ENV CAS_HOST=0.0.0.0
ENV CAS_PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
