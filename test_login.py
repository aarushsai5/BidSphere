import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect('d:/Auction Management System/database/app.db')
c = conn.cursor()
c.execute('SELECT password FROM users WHERE username="admin"')
row = c.fetchone()
if row:
    db_hash = row[0]
    print("DB HASH:", db_hash)
    print("MATCHES admin123:", check_password_hash(db_hash, "admin123"))
else:
    print("User admin not found in app.db")
