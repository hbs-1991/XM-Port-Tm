#!/bin/bash

# Development startup script for XM-Port

set -e

echo "🚀 Starting XM-Port Development Environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration"
fi

# Start services with Docker Compose
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run database migrations (when available)
echo "🗄️  Setting up database..."
# Uncomment when Python environment is set up:
# cd apps/api && python -m alembic upgrade head && cd ../..

# Start development servers
echo "🌟 Starting development servers..."
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "API Docs: http://localhost:8000/api/docs"

npm run dev