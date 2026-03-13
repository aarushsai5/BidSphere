import os
from dotenv import load_dotenv
load_dotenv()

print("DATABASE_URL loaded:", bool(os.environ.get("DATABASE_URL")))

from app import app, init_db, _use_postgres

with app.app_context():
    print("Using PostgreSQL:", _use_postgres())
    init_db()
    print("Tables created successfully!")

    from app import db_execute
    tables = db_execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()
    print("Tables in DB:", [t["tablename"] for t in tables])
    
    users = db_execute("SELECT COUNT(*) as c FROM users").fetchone()
    print("User count:", users["c"])
    print("\nAll good! Neon PostgreSQL is connected and ready.")
