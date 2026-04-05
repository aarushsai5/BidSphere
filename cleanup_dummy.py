"""Remove ALL dummy seed data from the database."""
from dotenv import load_dotenv
load_dotenv()
from app import app, db_execute, db_commit, _use_postgres

SEED_SELLERS = [
    "RoyalAntiques", "LuxuryAutoHub", "FineArtGallery", "EliteJewels",
    "TechPioneer", "HauteHorology", "VintageVault", "OpulentEstate",
    "ArtisanCraft", "PrimeCollectors", "GoldenEra", "SilkRouteArts",
    "demo_seller"
]
SEED_BIDDERS = ["LuxuryBidder"]

def cleanup():
    with app.app_context():
        db_type = 'PostgreSQL' if _use_postgres() else 'SQLite'
        print(f"Connected to {db_type}. Cleaning up all seed data...")

        if _use_postgres():
            all_users = SEED_SELLERS + SEED_BIDDERS
            # Delete bids on seed auctions
            db_execute("DELETE FROM bids WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username = ANY(%s)))", (all_users,))
            # Delete bids by seed bidder
            db_execute("DELETE FROM bids WHERE bidder_id IN (SELECT id FROM users WHERE username = ANY(%s))", (SEED_BIDDERS,))
            # Delete transactions on seed auctions
            db_execute("DELETE FROM transactions WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username = ANY(%s)))", (all_users,))
            # Delete seed auctions
            db_execute("DELETE FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username = ANY(%s))", (all_users,))
            # Delete seed reviews
            db_execute("DELETE FROM reviews WHERE user_id IN (SELECT id FROM users WHERE username = ANY(%s))", (all_users,))
            # Delete seed users
            db_execute("DELETE FROM users WHERE username = ANY(%s)", (all_users,))
        else:
            all_users = SEED_SELLERS + SEED_BIDDERS
            ph = ','.join('?' * len(all_users))
            db_execute(f"DELETE FROM bids WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username IN ({ph})))", tuple(all_users))
            db_execute(f"DELETE FROM bids WHERE bidder_id IN (SELECT id FROM users WHERE username IN ({ph}))", tuple(SEED_BIDDERS + [''] * (len(all_users) - len(SEED_BIDDERS))))
            try:
                db_execute(f"DELETE FROM transactions WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username IN ({ph})))", tuple(all_users))
            except Exception:
                pass
            db_execute(f"DELETE FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username IN ({ph}))", tuple(all_users))
            try:
                db_execute(f"DELETE FROM reviews WHERE user_id IN (SELECT id FROM users WHERE username IN ({ph}))", tuple(all_users))
            except Exception:
                pass
            db_execute(f"DELETE FROM users WHERE username IN ({ph})", tuple(all_users))

        db_commit()

        # Verify
        remaining_auctions = db_execute("SELECT COUNT(*) as c FROM auctions").fetchone()['c']
        remaining_users = db_execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
        print(f"\n✅ Cleanup complete!")
        print(f"   Remaining auctions: {remaining_auctions}")
        print(f"   Remaining users: {remaining_users}")

if __name__ == "__main__":
    cleanup()
