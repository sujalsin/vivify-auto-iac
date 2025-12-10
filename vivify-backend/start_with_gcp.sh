#!/bin/bash
# Start backend with GCP credentials automatically loaded

cd "$(dirname "$0")"

# Load GCP environment
source setup_gcp_env.sh

# Start backend
echo "Starting backend with GCP credentials..."
echo "Project: $GCP_PROJECT_ID"
echo ""
python main.py

