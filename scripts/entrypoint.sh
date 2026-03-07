#!/bin/bash
set -e

host="db"
port="5432"
timeout=30

echo "Waiting for PostgreSQL at $host:$port..."

for i in $(seq $timeout); do
  if nc -z "$host" "$port" 2>/dev/null; then
    echo "PostgreSQL is up - executing migrations"
    break
  fi
  echo "Waiting for PostgreSQL... ($i/$timeout)"
  sleep 1
done

if ! nc -z "$host" "$port" 2>/dev/null; then
  echo "PostgreSQL not available after $timeout seconds, exiting"
  exit 1
fi

echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully"
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload