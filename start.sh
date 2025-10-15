#!/bin/bash

# Car Assistant Bot - Startup Script

echo "🚗 Starting Car Assistant Bot..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy env.example to .env and configure it."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start the services
echo "📦 Starting services with Docker Compose..."
docker compose up -d

# Wait a moment for services to start
sleep 5

# Check if services are running
if docker compose ps | grep -q "Up"; then
    echo "✅ Services started successfully!"
    echo "📊 Service status:"
    docker compose ps
    echo ""
    echo "📝 To view logs: docker compose logs -f bot"
    echo "🛑 To stop: docker compose down"
else
    echo "❌ Failed to start services. Check logs with: docker compose logs"
    exit 1
fi
