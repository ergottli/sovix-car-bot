#!/bin/bash
set -e

echo "🚀 Starting Car Assistant Bot container..."

# Ожидание готовности базы данных
echo "⏳ Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if python3 << END
import asyncio
import asyncpg
import os
import sys

async def check_db():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        await conn.close()
        return True
    except Exception as e:
        return False

result = asyncio.run(check_db())
sys.exit(0 if result else 1)
END
    then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ PostgreSQL is not ready after $max_attempts attempts. Exiting."
        exit 1
    fi
    
    echo "⏳ Attempt $attempt/$max_attempts - waiting 2 seconds..."
    sleep 2
done

# Применение миграций Alembic
echo "🔄 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations applied successfully!"
else
    echo "❌ Failed to apply migrations!"
    exit 1
fi

# Запуск бота
echo "🤖 Starting bot..."
exec python bot.py

