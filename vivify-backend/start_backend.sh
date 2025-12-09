#!/bin/bash
# Start backend server for experiments

export DATABASE_URL="postgres://postgres:postgres@localhost:5433/vivify"

echo "Starting backend server..."
echo "Database: $DATABASE_URL"
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
echo ""

python main.py

