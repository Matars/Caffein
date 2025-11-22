#!/bin/bash

# Helper script to run Docker with AWS credentials from .env file
# Usage: ./run-with-aws.sh

set -e

echo "🔑 Loading AWS credentials from backend/.env file..."

# Check if .env file exists
if [ ! -f backend/.env ]; then
    echo "❌ Error: backend/.env file not found"
    echo "Please create backend/.env with AWS credentials"
    exit 1
fi

# Load environment variables from .env file
export $(grep -v '^#' backend/.env | grep -v '^$' | xargs)

# Verify credentials are loaded
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "❌ Error: AWS_ACCESS_KEY_ID not found in backend/.env"
    exit 1
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ Error: AWS_SECRET_ACCESS_KEY not found in backend/.env"
    exit 1
fi

# Set default region if not in .env
if [ -z "$AWS_DEFAULT_REGION" ]; then
    export AWS_DEFAULT_REGION="eu-central-1"
fi

echo "✅ AWS credentials loaded successfully"
echo "   Region: $AWS_DEFAULT_REGION"
echo "   Access Key: ${AWS_ACCESS_KEY_ID:0:8}..."

# Install frontend dependencies if package.json has changed
echo ""
echo "📦 Checking frontend dependencies..."
if [ -f frontend/package.json ]; then
    cd frontend
    if command -v pnpm &> /dev/null; then
        echo "   Installing/updating frontend dependencies with pnpm..."
        pnpm install
    else
        echo "⚠️  pnpm not found, skipping dependency installation"
        echo "   Dependencies will be installed in Docker container"
    fi
    cd ..
fi

# Run docker compose with credentials
echo ""
echo "🚀 Starting Docker Compose with AWS credentials..."
# Use -V to renew anonymous volumes (like /app/node_modules) to ensure fresh dependencies
docker compose up --build -V
