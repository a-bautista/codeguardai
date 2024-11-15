#!/bin/bash
set -e

echo "Starting application..."

# Export Flask app
export FLASK_APP=app.py

# Wait for database
python wait_for_db.py

# Start gunicorn
exec gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 2 --timeout 60 'app:app'