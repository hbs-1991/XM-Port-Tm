#!/bin/bash

# XM-Port Docker Stop Script

set -e

echo "🛑 Stopping XM-Port Development Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Use docker compose (newer) or docker-compose (legacy)
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Parse command line arguments
REMOVE_VOLUMES=false
REMOVE_IMAGES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        --images)
            REMOVE_IMAGES=true
            shift
            ;;
        --all)
            REMOVE_VOLUMES=true
            REMOVE_IMAGES=true
            shift
            ;;
        *)
            echo "Usage: $0 [--volumes] [--images] [--all]"
            echo "  --volumes: Remove named volumes (database data will be lost!)"
            echo "  --images: Remove built images"
            echo "  --all: Remove both volumes and images"
            exit 1
            ;;
    esac
done

# Stop and remove containers
print_status "Stopping services..."
$DOCKER_COMPOSE_CMD down --remove-orphans

if [ "$REMOVE_VOLUMES" = true ]; then
    print_status "Removing volumes (this will delete database data)..."
    $DOCKER_COMPOSE_CMD down -v
    docker volume prune -f
fi

if [ "$REMOVE_IMAGES" = true ]; then
    print_status "Removing built images..."
    docker image prune -f
    # Remove XM-Port specific images
    docker images | grep "xm-port" | awk '{print $3}' | xargs -r docker rmi -f
fi

print_success "XM-Port Development Environment stopped successfully!"

if [ "$REMOVE_VOLUMES" = true ]; then
    echo "⚠️  Database data has been removed. You'll need to run migrations again."
fi