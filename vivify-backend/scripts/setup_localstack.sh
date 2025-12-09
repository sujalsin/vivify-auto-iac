#!/bin/bash

# Setup script for LocalStack testing

echo "=========================================="
echo "LocalStack Setup Script"
echo "=========================================="

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if LocalStack is already running
if docker ps | grep -q localstack; then
    echo "✓ LocalStack is already running"
else
    echo "Starting LocalStack..."
    docker-compose up -d localstack
    
    # Wait for LocalStack to be ready
    echo "Waiting for LocalStack to be ready..."
    sleep 5
    
    # Check health
    if curl -s http://localhost:4566/_localstack/health | grep -q '"services":'; then
        echo "✓ LocalStack is ready"
    else
        echo "⚠ LocalStack may not be fully ready yet. Waiting a bit more..."
        sleep 5
    fi
fi

# Check if PostgreSQL is running
if docker ps | grep -q postgres; then
    echo "✓ PostgreSQL is already running"
else
    echo "Starting PostgreSQL..."
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    echo "Waiting for PostgreSQL to be ready..."
    sleep 3
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "LocalStack: http://localhost:4566"
echo "PostgreSQL: localhost:5432"
echo ""
echo "Next steps:"
echo "1. Run: python test_localstack.py"
echo "2. Initialize database: python -c 'from database.connection import init_db; import asyncio; asyncio.run(init_db())'"
echo "3. Run experiments via API or CLI"

