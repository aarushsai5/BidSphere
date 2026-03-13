-- ============================================================
-- Auction Management System — Database Schema (PostgreSQL)
-- ============================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    username    TEXT    NOT NULL UNIQUE,
    email       TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'bidder',   -- admin | seller | bidder
    is_banned   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auctions table
CREATE TABLE IF NOT EXISTS auctions (
    id              SERIAL PRIMARY KEY,
    seller_id       INTEGER NOT NULL,
    title           TEXT    NOT NULL,
    description     TEXT,
    image           TEXT,
    starting_price  REAL    NOT NULL,
    min_increment   REAL    NOT NULL DEFAULT 1.0,
    start_time      TEXT    NOT NULL,
    end_time        TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'upcoming',  -- upcoming | live | closed
    winner_id       INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (seller_id) REFERENCES users(id),
    FOREIGN KEY (winner_id) REFERENCES users(id)
);

-- Bids table
CREATE TABLE IF NOT EXISTS bids (
    id          SERIAL PRIMARY KEY,
    auction_id  INTEGER NOT NULL,
    bidder_id   INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE,
    FOREIGN KEY (bidder_id)  REFERENCES users(id)
);

-- Transactions table (payment simulation)
CREATE TABLE IF NOT EXISTS transactions (
    id          SERIAL PRIMARY KEY,
    auction_id  INTEGER NOT NULL UNIQUE,
    winner_id   INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending | completed
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE,
    FOREIGN KEY (winner_id)  REFERENCES users(id)
);
