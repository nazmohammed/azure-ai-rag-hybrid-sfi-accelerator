
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# System deps for spaCy/Presidio
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /app/backend/requirements.txt

COPY backend /app/backend
COPY data /app/data

EXPOSE 3978
CMD ["python", "backend/main.py"]
