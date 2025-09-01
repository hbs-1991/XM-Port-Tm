#!/bin/bash

# Production build script for XM-Port

set -e

echo "🏗️  Building XM-Port for production..."

# Install dependencies
echo "📦 Installing dependencies..."
npm ci

# Build shared packages first
echo "🔧 Building shared packages..."
npm run build --workspace=packages/shared

# Run tests
echo "🧪 Running tests..."
npm run test

# Run linting
echo "🔍 Running linter..."
npm run lint

# Build applications
echo "📦 Building applications..."
npm run build --workspace=apps/web

# Build Docker images for production
echo "🐳 Building Docker images..."
docker build -f Dockerfile.web --target production -t xm-port/web:latest .
docker build -f Dockerfile.api --target production -t xm-port/api:latest .

echo "✅ Build completed successfully!"
echo "Docker images:"
echo "  - xm-port/web:latest"
echo "  - xm-port/api:latest"