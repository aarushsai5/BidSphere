"""Seed admin user into the Neon PostgreSQL database."""
import os
from dotenv import load_dotenv
load_dotenv()

from werkzeug.security import generate_password_hash
from app import app, db_execute, db_commit, _use_postgres

with app.app_context():
    print("Using PostgreSQL:", _use_postgres())
    
    # Check if admin already exists
    existing = db_execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if existing:
        print("Admin user already exists! ID:", existing["id"])
    else:
        db_execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            ("admin", "admin@artandauction.com", generate_password_hash("admin123"), "admin")
        )
        db_commit()
        admin = db_execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
        print(f"Admin user created! ID: {admin['id']}")
    
    # Also count everything
    users = db_execute("SELECT COUNT(*) as c FROM users").fetchone()
    auctions = db_execute("SELECT COUNT(*) as c FROM auctions").fetchone()
    print(f"Total users: {users['c']}, Total auctions: {auctions['c']}")
    print("Done!")
