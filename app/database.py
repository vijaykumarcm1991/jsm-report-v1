import psycopg2
from app.config import DB_CONFIG
import time


def get_connection(retries=10, delay=3):
    for i in range(retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            print("✅ Connected to DB")
            return conn
        except Exception as e:
            print(f"⏳ DB not ready, retrying... ({i+1}/{retries})")
            time.sleep(delay)

    raise Exception("❌ Could not connect to DB after retries")

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        filters JSONB,
        fields JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()