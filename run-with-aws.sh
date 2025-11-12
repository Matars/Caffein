#!/bin/bash

# Helper script to run Docker with AWS credentials from the khaled profile
# Usage: ./run-with-aws.sh

set -e

echo "🔑 Loading AWS credentials from profile 'khaled'..."

# Extract credentials from AWS CLI profile
AWS_PROFILE_NAME="khaled"

# Read credentials from AWS CLI config
if [ ! -f ~/.aws/credentials ]; then
    echo "❌ Error: ~/.aws/credentials file not found"
    echo "Please run 'aws configure' first"
    exit 1
fi

# Extract credentials for the profile
export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id --profile $AWS_PROFILE_NAME)
export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key --profile $AWS_PROFILE_NAME)
export AWS_SESSION_TOKEN=$(aws configure get aws_session_token --profile $AWS_PROFILE_NAME 2>/dev/null || echo "")
export AWS_DEFAULT_REGION=$(aws configure get region --profile $AWS_PROFILE_NAME || echo "us-east-1")

# Verify credentials are loaded
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "❌ Error: Could not load AWS_ACCESS_KEY_ID from profile '$AWS_PROFILE_NAME'"
    exit 1
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ Error: Could not load AWS_SECRET_ACCESS_KEY from profile '$AWS_PROFILE_NAME'"
    exit 1
fi

echo "✅ AWS credentials loaded successfully"
echo "   Region: $AWS_DEFAULT_REGION"
echo "   Access Key: ${AWS_ACCESS_KEY_ID:0:8}..."
if [ -n "$AWS_SESSION_TOKEN" ]; then
    echo "   Session Token: Found (temporary credentials)"
fi

# Run docker compose with credentials
echo ""
echo "🚀 Starting Docker Compose with AWS credentials..."
docker compose up --build
