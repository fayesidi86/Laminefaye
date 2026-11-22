"""Create tables on Neon PostgreSQL by running schema.sql."""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

# Read schema.sql
script_dir = os.path.dirname(os.path.abspath(__file__))
schema_path = os.path.join(script_dir, "schema.sql")

if not os.path.exists(schema_path):
    print(f"ERROR: {schema_path} not found")
    sys.exit(1)

with open(schema_path, "r", encoding="utf-8") as f:
    schema_sql = f.read()

# Connect and execute
try:
    print(f"Connecting to Neon PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(schema_sql)
    cur.close()
    conn.close()
    print("Tables created successfully on Neon!")
    print("  - categories")
    print("  - products")
    print("  - settings")
    print("Default data inserted (categories + settings).")
except Exception as e:
    print(f"Error creating tables: {e}")
    sys.exit(1)
