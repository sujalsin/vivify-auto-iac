#!/bin/bash
# Setup GCP environment variables from key folder

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEY_FILE="$PROJECT_ROOT/key/patentsphere.json"

if [ ! -f "$KEY_FILE" ]; then
    echo "Error: GCP credentials file not found at $KEY_FILE"
    exit 1
fi

# Extract project ID from JSON
PROJECT_ID=$(python3 -c "import json; print(json.load(open('$KEY_FILE'))['project_id'])" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Could not extract project_id from $KEY_FILE"
    exit 1
fi

# Set environment variables
export GCP_PROJECT_ID="$PROJECT_ID"
export GOOGLE_APPLICATION_CREDENTIALS="$KEY_FILE"
export GCP_REGION="${GCP_REGION:-us-central1}"

# Also set DATABASE_URL if not already set
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5433/vivify"
fi

echo "✓ GCP environment configured:"
echo "  Project ID: $GCP_PROJECT_ID"
echo "  Credentials: $GOOGLE_APPLICATION_CREDENTIALS"
echo "  Region: $GCP_REGION"
echo "  Database: $DATABASE_URL"
echo ""
echo "Ready to run experiments!"

