#!/bin/bash

# Simple script to run the project with Docker Compose
# Usage: ./run.sh

set -e

echo "🚀 Starting Project VIS with Docker Compose..."

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Cleanup function to stop containers on exit
cleanup() {
    echo ""
    echo "🛑 Stopping containers..."
    docker compose down
    exit 0
}

trap cleanup SIGINT SIGTERM

# Build and start containers
echo "� Building and starting containers..."
docker compose up --build

echo ""
echo "✅ All services are running!"
echo "   MongoDB:  localhost:27017"
echo "   Backend:  http://localhost:5001"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
