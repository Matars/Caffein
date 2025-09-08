#!/bin/bash

# Development setup script
echo "🚀 Setting up 4DT911-ProjectVis development environment..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment and install dependencies
echo "🔧 Installing Python dependencies..."
source .venv/bin/activate
pip install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
pnpm install

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "⚠️  Docker is not running. Please start Docker Desktop first."
    echo ""
    echo "Manual setup options:"
    echo "1. Start MongoDB locally:"
    echo "   brew install mongodb-community"
    echo "   brew services start mongodb-community"
    echo ""
    echo "2. Start the development servers:"
    echo "   source .venv/bin/activate"
    echo "   pnpm dev"
    echo ""
    echo "Or use Docker:"
    echo "   docker-compose up"
    exit 1
fi

echo "✅ Docker is running!"
echo "📦 Starting services with Docker Compose..."

docker-compose up -d

echo ""
echo "🎉 Services started successfully!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend:  http://localhost:5000"
echo "🗄️  MongoDB: localhost:27017"
echo ""
echo "To stop services: docker-compose down"
echo "To view logs: docker-compose logs -f"
