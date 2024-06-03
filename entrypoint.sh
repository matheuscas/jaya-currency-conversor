#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Apply database migrations
echo "Applying database migrations..."
python currency_converter/manage.py migrate

# Start the server
echo "Starting server..."
exec "$@"
