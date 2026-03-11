-- ============================================================
-- Auction Management System — Database Schema (PostgreSQL)
-- ============================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    username    TEXT    NOT NULL UNIQUE,
    email       TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'bidder',
    is_banned   INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    status          TEXT    NOT NULL DEFAULT 'upcoming',
    winner_id       INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES users(id),
    FOREIGN KEY (winner_id) REFERENCES users(id)
);

-- Bids table
CREATE TABLE IF NOT EXISTS bids (
    id          SERIAL PRIMARY KEY,
    auction_id  INTEGER NOT NULL,
    bidder_id   INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(id),
    FOREIGN KEY (bidder_id)  REFERENCES users(id)
);

-- Transactions table (payment simulation)
CREATE TABLE IF NOT EXISTS transactions (
    id          SERIAL PRIMARY KEY,
    auction_id  INTEGER NOT NULL UNIQUE,
    winner_id   INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(id),
    FOREIGN KEY (winner_id)  REFERENCES users(id)
);
