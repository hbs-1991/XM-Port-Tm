#!/bin/bash

# XM-Port Docker Development Startup Script

set -e

echo "🚀 Starting XM-Port Development Environment with Docker..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    print_error "docker-compose is not available. Please install Docker Compose."
    exit 1
fi

# Use docker compose (newer) or docker-compose (legacy)
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Check if .env.docker exists and suggest copying
if [ ! -f ".env.local" ]; then
    if [ -f ".env.docker" ]; then
        print_warning ".env.local not found. You should copy .env.docker to .env.local and customize it."
        read -p "Would you like to copy .env.docker to .env.local now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.docker .env.local
            print_success "Copied .env.docker to .env.local"
            print_warning "Please edit .env.local and add your OPENAI_API_KEY"
        fi
    else
        print_error "Neither .env.local nor .env.docker found. Please create environment file."
        exit 1
    fi
fi

# Clean up any existing containers
print_status "Cleaning up existing containers..."
$DOCKER_COMPOSE_CMD down --remove-orphans

# Build and start services
print_status "Building and starting services..."
$DOCKER_COMPOSE_CMD up --build -d

# Wait for services to be healthy
print_status "Waiting for services to be ready..."

# Function to wait for service health
wait_for_health() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if $DOCKER_COMPOSE_CMD ps $service | grep -q "healthy"; then
            print_success "$service is healthy"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service failed to become healthy"
    return 1
}

# Wait for database
echo -n "Waiting for PostgreSQL"
wait_for_health postgres

# Wait for Redis  
echo -n "Waiting for Redis"
wait_for_health redis

# Wait for API
echo -n "Waiting for API"
wait_for_health api

# Wait for Web
echo -n "Waiting for Web"
wait_for_health web

print_success "All services are up and running!"

echo ""
echo "🎉 XM-Port Development Environment is ready!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔗 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🗄️  Database: localhost:5433"
echo "🔴 Redis: localhost:6379"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: $DOCKER_COMPOSE_CMD logs -f"
echo "  - View specific service logs: $DOCKER_COMPOSE_CMD logs -f [api|web|postgres|redis]"
echo "  - Stop services: $DOCKER_COMPOSE_CMD down"
echo "  - Restart service: $DOCKER_COMPOSE_CMD restart [service-name]"
echo "  - Shell into API: $DOCKER_COMPOSE_CMD exec api bash"
echo "  - Shell into Web: $DOCKER_COMPOSE_CMD exec web sh"
echo ""
echo "🔧 If you need to run database migrations:"
echo "  $DOCKER_COMPOSE_CMD exec api alembic upgrade head"
echo ""