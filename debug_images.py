from dotenv import load_dotenv
load_dotenv()
from app import app, db_execute
with app.app_context():
    rows = db_execute('SELECT id, title, image FROM auctions').fetchall()
    if not rows:
        print("No auctions in DB yet")
    for r in rows:
        img = r['image']
        print(f"ID={r['id']} | image={repr(img)} | starts_http={str(img).startswith('http') if img else 'N/A'}")
