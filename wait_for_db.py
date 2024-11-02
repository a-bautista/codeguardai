# wait_for_db.py
import time
import psycopg2
import os
from psycopg2 import OperationalError

def wait_for_db():
    max_retries = 30  # Maximum number of retries
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(
                dbname="flask_db",
                user="postgres",
                password="postgres",
                host="db",  # Use the service name from docker-compose
                port="5432"
            )
            conn.close()
            print("Successfully connected to the database!")
            return True
        except OperationalError as e:
            retry_count += 1
            print(f"Waiting for database... {retry_count}/{max_retries}")
            print(f"Error: {e}")
            time.sleep(2)  # Wait 2 seconds before retrying
    
    print("Could not connect to the database after maximum retries")
    return False

if __name__ == "__main__":
    wait_for_db()