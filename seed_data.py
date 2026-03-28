"""Seed comprehensive dummy data with multiple sellers and high-quality images."""
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

from werkzeug.security import generate_password_hash
from app import app, db_execute, db_commit, _use_postgres

# Enhanced Sellers List
SELLERS = [
    {"username": "RoyalAntiques", "email": "contact@royalantiques.com", "verified": True},
    {"username": "LuxuryAutoHub", "email": "sales@luxuryauto.com", "verified": False},
    {"username": "FineArtGallery", "email": "curator@fineart.com", "verified": True},
    {"username": "EliteJewels", "email": "info@elitejewels.com", "verified": False},
    {"username": "TechPioneer", "email": "support@techpioneer.com", "verified": False},
]

# High-Quality, Relevant Images from Unsplash
DUMMY_AUCTIONS = [
    {
        "category": "antique",
        "seller": "RoyalAntiques",
        "title": "18th Century Victorian Vase",
        "description": "Exquisite porcelain vase from the Victorian era with intricate floral gold leaf gilding. A rare collector's piece in pristine condition.",
        "image": "https://images.unsplash.com/photo-1581024317772-88229a435889?q=80&w=1000",
        "starting_price": 45000.0,
        "status": "live"
    },
    {
        "category": "car",
        "seller": "LuxuryAutoHub",
        "title": "Classic Red Sports Coupe",
        "description": "Vintage luxury sports car in racing red. Original leather seats, manually polished chrome, and a roaring V8 engine.",
        "image": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?q=80&w=1000",
        "starting_price": 2800000.0,
        "status": "upcoming"
    },
    {
        "category": "art",
        "seller": "FineArtGallery",
        "title": "Sunset over Mountains Canvas",
        "description": "Original oil-on-canvas landscape painting showing a breathtaking sunset. Professional frame included.",
        "image": "https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?q=80&w=1000",
        "starting_price": 55000.0,
        "status": "live"
    },
    {
        "category": "jewelry",
        "seller": "EliteJewels",
        "title": "Diamond Engagement Ring",
        "description": "Brilliant-cut 2-carat diamond set in a platinum band. Comes with a GIA certificate. Timeless elegance.",
        "image": "https://images.unsplash.com/photo-1605100804763-247f67b3557e?q=80&w=1000",
        "starting_price": 150000.0,
        "status": "closed"
    },
    {
        "category": "electronics",
        "seller": "TechPioneer",
        "title": "Professional Drone Kit",
        "description": "High-end 4K camera drone with dual flight batteries, professional remote, and hard-shell carrying case.",
        "image": "https://images.unsplash.com/photo-1507584175317-bf49ea636a0d?q=80&w=1000",
        "starting_price": 85000.0,
        "status": "live"
    },
    {
        "category": "antique",
        "seller": "RoyalAntiques",
        "title": "Antique Gramophone",
        "description": "Fully functional vintage gramophone with brass horn. Includes a small collection of original vinyl records.",
        "image": "https://images.unsplash.com/photo-1525044439130-141a0842db74?q=80&w=1000",
        "starting_price": 32000.0,
        "status": "upcoming"
    },
    {
        "category": "jewelry",
        "seller": "EliteJewels",
        "title": "Gold Emerald Earrings",
        "description": "Pair of deep green emerald earrings surrounded by small pavé diamonds. 14K yellow gold setting.",
        "image": "https://images.unsplash.com/photo-1535633302704-b04044a1074e?q=80&w=1000",
        "starting_price": 42000.0,
        "status": "live"
    },
    {
        "category": "car",
        "seller": "LuxuryAutoHub",
        "title": "Modern Electric Supercar",
        "description": "Futuristic electric supercar with 1000+ HP. Carbon fiber body, minimalist interior, and unmatched acceleration.",
        "image": "https://images.unsplash.com/photo-1614162692292-7ac56d7f7f1e?q=80&w=1000",
        "starting_price": 5500000.0,
        "status": "live"
    }
]

def seed():
    with app.app_context():
        print(f"Connecting to {'PostgreSQL' if _use_postgres() else 'SQLite'}...")
        
        # Clear existing dummy data first to avoid clutter
        try:
            db_execute("DELETE FROM bids WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username IN %s))", (tuple(s["username"] for s in SELLERS) + ('demo_seller',),))
            db_execute("DELETE FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username IN %s)", (tuple(s["username"] for s in SELLERS) + ('demo_seller',),))
            db_commit()
            print("Cleared previous dummy data.")
        except Exception as e:
            print("Notice: Could not clear previous data (might not exist).", e)

        # 1. Ensure Sellers exist
        seller_map = {}
        for s_data in SELLERS:
            seller = db_execute("SELECT id FROM users WHERE username = ?", (s_data["username"],)).fetchone()
            if not seller:
                db_execute(
                    "INSERT INTO users (username, email, password, role, is_verified) VALUES (?, ?, ?, ?, ?)",
                    (s_data["username"], s_data["email"], generate_password_hash("demo123"), "seller", s_data["verified"])
                )
                db_commit()
                seller = db_execute("SELECT id FROM users WHERE username = ?", (s_data["username"],)).fetchone()
                print(f"Created seller: {s_data['username']}")
            
            seller_map[s_data["username"]] = seller["id"]

        # 2. Add Auctions
        now = datetime.utcnow()
        for item in DUMMY_AUCTIONS:
            seller_id = seller_map[item["seller"]]
            
            # Set times based on status
            if item["status"] == "live":
                start_time = now - timedelta(days=1)
                end_time = now + timedelta(days=3)
            elif item["status"] == "upcoming":
                start_time = now + timedelta(days=2)
                end_time = now + timedelta(days=5)
            else: # closed
                start_time = now - timedelta(days=10)
                end_time = now - timedelta(days=1)
            
            start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

            db_execute(
                "INSERT INTO auctions (seller_id, title, description, image, starting_price, min_increment, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (seller_id, item["title"], item["description"], item["image"], item["starting_price"], 1000.0, start_str, end_str, item["status"])
            )
            db_commit()
            
            auction_id = db_execute("SELECT id FROM auctions ORDER BY id DESC LIMIT 1").fetchone()["id"]
            
            if item["status"] in ["live", "closed"]:
                # Add 1-3 dummy bids
                bidder = db_execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
                if bidder:
                    num_bids = random.randint(1, 3)
                    curr_price = item["starting_price"]
                    for _ in range(num_bids):
                        curr_price += random.randint(5000, 20000)
                        db_execute(
                            "INSERT INTO bids (auction_id, bidder_id, amount) VALUES (?, ?, ?)",
                            (auction_id, bidder["id"], curr_price)
                        )
                    db_commit()
                    print(f"Added {num_bids} bids to '{item['title']}'")

        # 3. Add 10 successful dummy transactions for verified sellers
        print("Generating dummy successful trades for verified sellers...")
        verification_buyer = db_execute("SELECT id FROM users WHERE role = 'buyer' LIMIT 1").fetchone()
        
        for s_data in SELLERS:
            if s_data["verified"] and verification_buyer:
                seller_id = seller_map[s_data["username"]]
                for i in range(10):
                    # add a dummy closed auction
                    db_execute(
                        "INSERT INTO auctions (seller_id, title, description, starting_price, min_increment, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (seller_id, f"Dummy Setup Auction {i}", "System generated", 100, 10, "2023-01-01 00:00:00", "2023-01-02 00:00:00", "closed")
                    )
                    dummy_auction_id = db_execute("SELECT id FROM auctions ORDER BY id DESC LIMIT 1").fetchone()["id"]
                    # add transaction
                    db_execute(
                        "INSERT INTO transactions (auction_id, buyer_id, amount, status) VALUES (?, ?, ?, ?)",
                        (dummy_auction_id, verification_buyer["id"], 150.0, "completed")
                    )
                db_commit()
                print(f"Added 10 successful dummy trades for {s_data['username']}")

        print("Successfully seeded enhanced dummy data!")

if __name__ == "__main__":
    seed()
