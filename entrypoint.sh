#!/bin/bash
set -e

# Export Flask app
export FLASK_APP=app.py

# Wait for database if needed
python wait_for_db.py

# Initialize database if it doesn't exist
if [ ! -d "migrations" ]; then
    flask db init
fi

# Run migrations
flask db migrate -m "Initial migration" || true
flask db upgrade

# Start gunicorn
exec gunicorn --bind :8080 --workers 2 --threads 4 --timeout 60 app:app