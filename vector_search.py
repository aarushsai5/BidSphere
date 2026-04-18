"""
vector_search.py — Semantic Vector Search + AI Summary for Art&Auction
Uses Hugging Face free Inference API for embeddings & text generation.
Stores vectors in PostgreSQL via pgvector extension (Neon-compatible).
"""

import os
import json
import requests
import time

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

HF_API_TOKEN = os.environ.get('HF_API_TOKEN', '')
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SUMMARY_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
EMBEDDING_DIM = 384

HF_EMBED_URL = f"https://api-inference.huggingface.co/models/{EMBEDDING_MODEL}"
HF_SUMMARY_URL = f"https://api-inference.huggingface.co/models/{SUMMARY_MODEL}"


def _hf_headers():
    return {"Authorization": f"Bearer {HF_API_TOKEN}"}


# ─────────────────────────────────────────────────────────────
# Schema — run once to create pgvector table
# ─────────────────────────────────────────────────────────────

def ensure_vector_schema(conn):
    """Create the pgvector extension and auction_embeddings table if missing."""
    cur = conn.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[vector_search] pgvector extension note: {e}")

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS auction_embeddings (
                id          SERIAL PRIMARY KEY,
                auction_id  INTEGER NOT NULL UNIQUE REFERENCES auctions(id) ON DELETE CASCADE,
                embedding   vector(384) NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_auction_embeddings_ivfflat
            ON auction_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10);
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        # IVFFlat index may fail if < 10 rows; that's OK — falls back to exact scan
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auction_embeddings (
                    id          SERIAL PRIMARY KEY,
                    auction_id  INTEGER NOT NULL UNIQUE REFERENCES auctions(id) ON DELETE CASCADE,
                    embedding   vector(384) NOT NULL,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            conn.commit()
        except Exception as e2:
            conn.rollback()
            print(f"[vector_search] schema creation note: {e2}")
    cur.close()


# ─────────────────────────────────────────────────────────────
# Embeddings — Hugging Face Inference API
# ─────────────────────────────────────────────────────────────

from huggingface_hub import InferenceClient

def get_embedding(text, retries=3):
    """
    Get a 384-dim embedding for the given text via HF Inference API.
    Returns a list of floats, or None on failure.
    """
    if not HF_API_TOKEN:
        print("[vector_search] WARNING: HF_API_TOKEN not set")
        return None

    # Clean and truncate text
    clean_text = ' '.join((text or '').split())[:1000]
    if not clean_text:
        return None

    client = InferenceClient(api_key=HF_API_TOKEN)
    
    for attempt in range(retries):
        try:
            # Use the official client to get feature extraction
            # Some models return a list of floats directly, others a list of lists (tokens)
            v = client.feature_extraction(clean_text, model=EMBEDDING_MODEL)
            
            # Handle different response types locally
            import numpy as np
            vec = np.array(v)
            
            if vec.ndim == 1:
                if vec.shape[0] == EMBEDDING_DIM:
                    return vec.tolist()
            elif vec.ndim == 2:
                # Mean pool token embeddings
                pooled = np.mean(vec, axis=0)
                if pooled.shape[0] == EMBEDDING_DIM:
                    return pooled.tolist()
            elif vec.ndim == 3:
                # Handle batch format [[[...]]]
                pooled = np.mean(vec[0], axis=0)
                if pooled.shape[0] == EMBEDDING_DIM:
                    return pooled.tolist()

            print(f"[vector_search] Unexpected embedding shape: {vec.shape}")
            return None
        except Exception as e:
            print(f"[vector_search] Embedding error (attempt {attempt+1}): {e}")
            if "503" in str(e) or "loading" in str(e).lower():
                time.sleep(15)
                continue
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


# ─────────────────────────────────────────────────────────────
# Indexing — store auction embeddings
# ─────────────────────────────────────────────────────────────

def index_auction(conn, auction_id, title, description):
    """Generate and store embedding for a single auction."""
    import psycopg2.extras

    # Combine title + description for richer semantic content
    desc_clean = (description or '').replace('**Category:**', 'Category:').replace('**Condition:**', 'Condition:')
    text = f"{title}. {desc_clean}"
    embedding = get_embedding(text)
    if embedding is None:
        return False

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Upsert: insert or update if exists
        cur.execute("""
            INSERT INTO auction_embeddings (auction_id, embedding)
            VALUES (%s, %s::vector)
            ON CONFLICT (auction_id)
            DO UPDATE SET embedding = EXCLUDED.embedding, created_at = now()
        """, (auction_id, str(embedding)))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[vector_search] Index error for auction {auction_id}: {e}")
        return False
    finally:
        cur.close()


def index_all_auctions(conn):
    """Index all auctions that don't have embeddings yet. Returns count indexed."""
    import psycopg2.extras
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT a.id, a.title, a.description
            FROM auctions a
            LEFT JOIN auction_embeddings ae ON a.id = ae.auction_id
            WHERE ae.id IS NULL
            ORDER BY a.id
        """)
        rows = cur.fetchall()
    except Exception as e:
        print(f"[vector_search] Query error: {e}")
        return 0
    finally:
        cur.close()

    count = 0
    for row in rows:
        success = index_auction(conn, row['id'], row['title'], row['description'])
        if success:
            count += 1
        # Small delay to respect HF rate limits
        time.sleep(0.5)

    print(f"[vector_search] Indexed {count}/{len(rows)} auctions")
    return count


# ─────────────────────────────────────────────────────────────
# Search — cosine similarity via pgvector
# ─────────────────────────────────────────────────────────────

def search_similar(conn, query_text, top_k=5):
    """
    Find the top_k most similar auctions to the query text.
    Returns list of dicts with auction data + similarity score.
    """
    import psycopg2.extras

    query_embedding = get_embedding(query_text)
    if query_embedding is None:
        return []

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT
                a.id,
                a.title,
                a.description,
                a.image,
                a.starting_price,
                a.status,
                a.start_time,
                a.end_time,
                a.seller_id,
                u.username AS seller_name,
                1 - (ae.embedding <=> %s::vector) AS similarity
            FROM auction_embeddings ae
            JOIN auctions a ON ae.auction_id = a.id
            JOIN users u ON a.seller_id = u.id
            ORDER BY ae.embedding <=> %s::vector
            LIMIT %s
        """, (str(query_embedding), str(query_embedding), top_k))
        results = cur.fetchall()

        # Enrich with bid info
        enriched = []
        for row in results:
            r = dict(row)
            cur.execute("""
                SELECT COUNT(*) as bid_count, MAX(amount) as highest_bid
                FROM bids WHERE auction_id = %s
            """, (r['id'],))
            bids = cur.fetchone()
            r['bid_count'] = bids['bid_count'] if bids else 0
            r['highest_bid'] = float(bids['highest_bid']) if bids and bids['highest_bid'] else None
            r['current_price'] = r['highest_bid'] or float(r['starting_price'])
            r['similarity'] = round(float(r['similarity']) * 100, 1)
            # Convert non-serializable types
            r['starting_price'] = float(r['starting_price'])
            for dt_field in ('start_time', 'end_time'):
                if hasattr(r[dt_field], 'isoformat'):
                    r[dt_field] = r[dt_field].isoformat()
                else:
                    r[dt_field] = str(r[dt_field]) if r[dt_field] else ''
            enriched.append(r)

        return enriched
    except Exception as e:
        print(f"[vector_search] Search error: {e}")
        return []
    finally:
        cur.close()


# ─────────────────────────────────────────────────────────────
# AI Summary — Hugging Face text generation
# ─────────────────────────────────────────────────────────────

def generate_summary(results, query):
    """
    Generate an AI summary of the search results using HF text generation.
    Falls back to a template-based summary if API fails.
    """
    if not results:
        return "No matching auctions found for your search."

    if not HF_API_TOKEN:
        return _fallback_summary(results, query)

    # Build context from top results
    items = []
    for i, r in enumerate(results[:3], 1):
        desc = (r.get('description', '') or '')[:150]
        items.append(f"{i}. \"{r['title']}\" — ₹{r['current_price']:,.0f} ({r['status']}) — {desc}")

    prompt = f"""<s>[INST] You are an auction assistant for Art&Auction, an Indian auction platform.
A user searched for: "{query}"

Top matching items:
{chr(10).join(items)}

Write a brief, helpful 2-3 sentence summary of these results. Mention prices in ₹ (INR).
Be concise and enthusiastic. Do NOT use markdown. [/INST]"""

    try:
        client = InferenceClient(api_key=HF_API_TOKEN)
        
        # Use simple text generation with the model
        response = client.text_generation(
            prompt,
            model=SUMMARY_MODEL,
            max_new_tokens=150,
            temperature=0.7,
            stop_sequences=["</s>"]
        )
        
        if response:
            return response.strip()

        return _fallback_summary(results, query)
    except Exception as e:
        print(f"[vector_search] Summary error: {e}")
        if "503" in str(e) or "loading" in str(e).lower():
            # Wait a bit if model is loading, but return fallback for immediate UX
            pass
        return _fallback_summary(results, query)


def _fallback_summary(results, query):
    """Template-based fallback when HF API is unavailable."""
    count = len(results)
    if count == 0:
        return "No matching auctions found for your search."

    top = results[0]
    prices = [r['current_price'] for r in results]
    avg_price = sum(prices) / len(prices)

    summary = f"Found {count} auction{'s' if count > 1 else ''} matching \"{query}\". "
    summary += f"The best match is \"{top['title']}\" at ₹{top['current_price']:,.0f} "
    summary += f"with a {top['similarity']}% relevance score. "
    if count > 1:
        summary += f"Prices range from ₹{min(prices):,.0f} to ₹{max(prices):,.0f}."
    return summary
