# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies early to leverage caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the backend source code and migrations.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["./start.sh"]
