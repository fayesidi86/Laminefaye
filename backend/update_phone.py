import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("UPDATE settings SET whatsapp_phone = '22377219028' WHERE key = 'main'")
conn.commit()
cur.execute("SELECT whatsapp_phone, store_name, currency FROM settings WHERE key = 'main'")
row = cur.fetchone()
print("Settings mis a jour:")
print(f"  Telephone: {row[0]}")
print(f"  Boutique : {row[1]}")
print(f"  Monnaie  : {row[2]}")
cur.close()
conn.close()
print("OK!")
