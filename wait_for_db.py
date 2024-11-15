import time
import psycopg2
import os
from urllib.parse import urlparse

def wait_for_db():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise Exception("DATABASE_URL environment variable is not set")
    
    # Convert postgres:// to postgresql:// if necessary
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    parsed = urlparse(db_url)
    db_params = {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432
    }

    max_retries = 30
    retry_interval = 2

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(**db_params)
            conn.close()
            print("Successfully connected to the database")
            return
        except psycopg2.OperationalError as e:
            print(f"Attempt {i+1}/{max_retries}: Database not ready yet: {e}")
            time.sleep(retry_interval)

    raise Exception("Could not connect to the database after maximum retries")

if __name__ == "__main__":
    wait_for_db()