from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import requests
import os
import time
from werkzeug.security import generate_password_hash, check_password_hash

# Load .env file for local development (no-op in production)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Neon sends `channel_binding=require` in the URL which psycopg2 doesn't support
# Strip it out so psycopg2 can connect cleanly (SSL is still enforced via sslmode=require)
# Also aggressively strip whitespace/newlines which might have been pasted from Windows
_raw_db_url = app.config.get('DATABASE_URL', '').strip()
if _raw_db_url:
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(_raw_db_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    if 'channel_binding' in params:
        params.pop('channel_binding', None)
        new_query = urlencode({k: v[0] for k, v in params.items()})
        _raw_db_url = urlunparse(parsed._replace(query=new_query))
    # Update the config with the cleaned URL
    app.config['DATABASE_URL'] = _raw_db_url.strip()


# ─────────────────────────────────────────────────────────────
# Database — PostgreSQL via psycopg2
# Falls back to SQLite for local dev if DATABASE_URL is not set
# ─────────────────────────────────────────────────────────────

def _use_postgres():
    return bool(app.config.get('DATABASE_URL'))

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        if _use_postgres():
            import psycopg2
            import psycopg2.extras
            db_url = app.config['DATABASE_URL']
            conn = psycopg2.connect(db_url)
            conn.autocommit = False
            db = g._database = conn
        else:
            import sqlite3
            conn = sqlite3.connect(app.config['DATABASE'])
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.row_factory = sqlite3.Row
            db = g._database = conn
    return db

def db_execute(query, params=()):
    """Execute a query and return a cursor. Handles ? vs %s differences."""
    conn = get_db()
    if _use_postgres():
        import psycopg2.extras
        # Convert SQLite-style ? placeholders to %s for psycopg2
        pg_query = query.replace('?', '%s')
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(pg_query, params)
        return cur
    else:
        return conn.execute(query, params)

def db_commit():
    """Commit the current transaction."""
    conn = get_db()
    conn.commit()

def db_lastrowid(cur):
    """Get the last inserted row ID in a cross-DB way."""
    if _use_postgres():
        # For INSERT ... RETURNING id, use fetchone()
        # Otherwise fall back to lastval()
        try:
            row = cur.fetchone()
            if row:
                return row['id'] if hasattr(row, 'keys') else row[0]
        except Exception:
            pass
        # fallback: query lastval
        c = get_db().cursor()
        c.execute("SELECT lastval()")
        return c.fetchone()[0]
    else:
        return cur.lastrowid

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    email       TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'bidder',
    is_banned   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS auctions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
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
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (seller_id) REFERENCES users(id),
    FOREIGN KEY (winner_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS bids (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id  INTEGER NOT NULL,
    bidder_id   INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (auction_id) REFERENCES auctions(id),
    FOREIGN KEY (bidder_id)  REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id  INTEGER NOT NULL UNIQUE,
    winner_id   INTEGER NOT NULL,
    amount      REAL    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pending',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (auction_id) REFERENCES auctions(id),
    FOREIGN KEY (winner_id)  REFERENCES users(id)
);
"""

def init_db():
    """Create tables. Uses PostgreSQL schema.sql on Vercel, inline SQLite schema locally."""
    with app.app_context():
        conn = get_db()
        if _use_postgres():
            with app.open_resource('database/schema.sql', mode='r') as f:
                schema = f.read()
            cur = conn.cursor()
            cur.execute(schema)
            conn.commit()
        else:
            conn.executescript(_SQLITE_SCHEMA)
            conn.commit()
        print("DB initialized successfully.")

# ─────────────────────────────────────────────────────────────
# Image upload helpers
# ─────────────────────────────────────────────────────────────

def process_image_to_datauri(image_file, filename, max_size=800, quality=80):
    """
    Convert an uploaded image to a compressed base64 data URI.
    Stored directly in the DB — no CDN, no Blob access issues.
    Resizes to max_size x max_size and compresses as JPEG.
    """
    try:
        import base64, io
        from PIL import Image as PILImage

        image_file.seek(0)
        img = PILImage.open(image_file)

        # Convert RGBA/palette to RGB for JPEG
        if img.mode in ('RGBA', 'P', 'LA'):
            background = PILImage.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize maintaining aspect ratio
        img.thumbnail((max_size, max_size), PILImage.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"
    except ImportError:
        # Pillow not installed — fall back to raw base64
        import base64
        image_file.seek(0)
        raw = image_file.read()
        ext = filename.rsplit('.', 1)[-1].lower()
        mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
                'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/jpeg')
        b64 = base64.b64encode(raw).decode('utf-8')
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"Image processing error: {e}")
        return ''


# ─────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────

class User:
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        row = db_execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if row:
            g.user = User(id=row['id'], username=row['username'],
                          email=row['email'], role=row['role'])
        else:
            g.user = None

@app.context_processor
def inject_user():
    return dict(current_user=g.user)

@app.template_filter('format_ist')
def format_ist(value):
    return value

@app.template_filter('format_date')
def format_date(value):
    """Return YYYY-MM-DD date string from a datetime object or ISO string safely."""
    if value is None:
        return ''
    try:
        # PostgreSQL returns actual datetime/date objects
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        # SQLite returns strings like '2026-03-20T22:30' or '2026-03-20 22:30:00'
        return str(value).split('T')[0].split(' ')[0]
    except Exception:
        return str(value)

# ─────────────────────────────────────────────────────────────
# Debug route
# ─────────────────────────────────────────────────────────────

@app.route('/debug/db-status')
def db_status():
    status = {'using_postgres': _use_postgres()}
    try:
        count = db_execute("SELECT COUNT(*) as c FROM auctions").fetchone()
        status['auction_count'] = count['c'] if count else 0
        ucount = db_execute("SELECT COUNT(*) as c FROM users").fetchone()
        status['user_count'] = ucount['c'] if ucount else 0
    except Exception as e:
        status['error'] = str(e)
    return status

@app.route('/debug/image-check')
def image_check():
    """Diagnostic route to check the last 5 auctions' image data."""
    try:
        rows = db_execute("SELECT id, title, image FROM auctions ORDER BY id DESC LIMIT 5").fetchall()
        results = []
        for r in rows:
            img = r['image'] or ''
            results.append({
                'id': r['id'],
                'title': r['title'],
                'image_data_length': len(img),
                'image_prefix': img[:50] + '...' if len(img) > 50 else img,
                'is_base64': img.startswith('data:image')
            })
        return {'last_5_auctions': results, 'postgres': _use_postgres()}
    except Exception as e:
        return {'error': str(e)}

# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    status_filter = request.args.get('status', 'all')
    search = request.args.get('q', '')

    query = 'SELECT * FROM auctions WHERE 1=1'
    params = []

    if status_filter != 'all':
        query += ' AND status = ?'
        params.append(status_filter)
    if search:
        query += ' AND (title ILIKE ? OR description ILIKE ?)' if _use_postgres() else ' AND (title LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    auctions_rows = db_execute(query, params).fetchall()

    auctions = []
    for row in auctions_rows:
        seller = db_execute('SELECT username FROM users WHERE id = ?', (row['seller_id'],)).fetchone()
        bids = db_execute('SELECT COUNT(*) as c, MAX(amount) as m FROM bids WHERE auction_id = ?', (row['id'],)).fetchone()
        auc = dict(row)
        auc['seller_name'] = seller['username'] if seller else 'Unknown'
        auc['bid_count'] = bids['c'] if bids else 0
        auc['highest_bid'] = bids['m'] if bids['m'] else None
        auctions.append(auc)

    return render_template('index.html', auctions=auctions,
                           status_filter=status_filter, search=search)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = db_execute('SELECT * FROM users WHERE username = ? OR email = ?',
                          (username, username)).fetchone()

        if user is None:
            flash('Incorrect username or email.', 'danger')
        elif not check_password_hash(str(user['password']), password):
            flash('Incorrect password.', 'danger')
        elif user['is_banned']:
            flash('This account is banned.', 'danger')
        else:
            session.clear()
            session['user_id'] = user['id']
            flash('Successfully logged in.', 'success')
            return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'bidder')

        error = None
        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif db_execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            error = f"User {username} is already registered."
        elif db_execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            error = f"Email {email} is already registered."

        if error is None:
            db_execute(
                'INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                (username, email, generate_password_hash(password), role)
            )
            db_commit()

            user = db_execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            session.clear()
            session['user_id'] = user['id']
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))

        flash(error, 'danger')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/create-auction', methods=['GET', 'POST'])
def create_auction():
    if not g.user or g.user.role not in ('seller', 'admin'):
        flash('You must be a seller to list items.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        starting_price = request.form.get('starting_price')
        min_increment = request.form.get('min_increment')
        category = request.form.get('category', 'misc').capitalize()
        condition = request.form.get('condition', 'good').capitalize()
        notes = request.form.get('condition_notes', '')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        full_desc = f"**Category:** {category}\n**Condition:** {condition}\n**Condition Notes:** {notes}\n\n{description}"

        # ── Image handling ──────────────────────────────────
        # Check for client-side compressed base64 first
        image_base64 = request.form.get('image_base64')
        image_url = ''
        
        if image_base64 and image_base64.startswith('data:image'):
            # Use client-side compressed image
            image_url = image_base64
            print(f"DEBUG: Using client-side base64 image. Length: {len(image_url)}")
        else:
            # Fallback to server-side processing if no client-side base64
            image_file = request.files.get('image')
            if image_file and image_file.filename:
                import werkzeug.utils
                filename = werkzeug.utils.secure_filename(image_file.filename)
                image_url = process_image_to_datauri(image_file, filename)
                if not image_url:
                    if not os.environ.get('VERCEL'):
                        upload_path = app.config['UPLOAD_FOLDER']
                        os.makedirs(upload_path, exist_ok=True)
                        image_file.seek(0)
                        image_file.save(os.path.join(upload_path, filename))
                        image_url = filename

        if not start_time:
            from datetime import datetime
            start_time = datetime.now().strftime('%Y-%m-%dT%H:%M')

        db_execute(
            'INSERT INTO auctions (seller_id, title, description, image, starting_price, min_increment, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (g.user.id, title, full_desc, image_url, starting_price, min_increment, start_time, end_time, 'live')
        )
        db_commit()

        flash('Auction created successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('create_auction.html')


@app.route('/dashboard')
def dashboard():
    if not g.user:
        flash('Please login to view your dashboard.', 'danger')
        return redirect(url_for('login'))

    auctions = []
    if g.user.role in ('seller', 'admin'):
        rows = db_execute(
            'SELECT * FROM auctions WHERE seller_id = ? ORDER BY created_at DESC',
            (g.user.id,)
        ).fetchall()
        for row in rows:
            bids = db_execute(
                'SELECT COUNT(*) as c, MAX(amount) as m FROM bids WHERE auction_id = ?',
                (row['id'],)
            ).fetchone()
            auc = dict(row)
            auc['bid_count'] = bids['c'] if bids else 0
            auc['highest_bid'] = bids['m'] if bids['m'] else None
            auctions.append(auc)
    else:
        query = '''
            SELECT DISTINCT a.* FROM auctions a
            JOIN bids b ON a.id = b.auction_id
            WHERE b.bidder_id = ? ORDER BY a.created_at DESC
        '''
        rows = db_execute(query, (g.user.id,)).fetchall()
        for row in rows:
            bids = db_execute('SELECT MAX(amount) as m FROM bids WHERE auction_id = ?', (row['id'],)).fetchone()
            user_bid = db_execute(
                'SELECT MAX(amount) as m FROM bids WHERE auction_id = ? AND bidder_id = ?',
                (row['id'], g.user.id)
            ).fetchone()
            auc = dict(row)
            auc['highest_bid'] = bids['m'] if bids['m'] else None
            auc['my_bid'] = user_bid['m'] if user_bid['m'] else None
            auc['is_winning'] = auc['highest_bid'] == auc['my_bid']
            auctions.append(auc)

    return render_template('dashboard.html', auctions=auctions)


@app.route('/auction/<int:auction_id>')
def auction_detail(auction_id):
    row = db_execute('SELECT * FROM auctions WHERE id = ?', (auction_id,)).fetchone()
    if not row:
        flash('Auction not found.', 'danger')
        return redirect(url_for('index'))

    auction = dict(row)
    seller = db_execute('SELECT username FROM users WHERE id = ?', (auction['seller_id'],)).fetchone()
    auction['seller_name'] = seller['username'] if seller else 'Unknown'

    bids = db_execute('''
        SELECT b.amount, b.created_at, u.username as bidder_name
        FROM bids b
        JOIN users u ON b.bidder_id = u.id
        WHERE b.auction_id = ?
        ORDER BY b.amount DESC
    ''', (auction_id,)).fetchall()

    current_bid = bids[0]['amount'] if bids else auction['starting_price']

    return render_template('auction_detail.html', auction=auction,
                           bids=bids, current_bid=current_bid)


@app.route('/auction/<int:auction_id>/bid', methods=['POST'])
def place_bid(auction_id):
    if not g.user:
        flash('You must be logged in to place a bid.', 'danger')
        return redirect(url_for('login'))

    if g.user.role == 'seller':
        flash('Sellers cannot place bids.', 'danger')
        return redirect(url_for('index'))

    amount = float(request.form.get('amount', 0))

    auction = db_execute('SELECT * FROM auctions WHERE id = ?', (auction_id,)).fetchone()
    if not auction:
        flash('Auction not found.', 'danger')
        return redirect(url_for('index'))

    if auction['status'] != 'live':
        flash('This auction is not currently active.', 'danger')
        return redirect(url_for('auction_detail', auction_id=auction_id))

    highest = db_execute('SELECT MAX(amount) as m FROM bids WHERE auction_id = ?', (auction_id,)).fetchone()
    current_highest = highest['m'] if highest['m'] else auction['starting_price']

    min_bid = current_highest + auction['min_increment']
    if amount < min_bid:
        flash(f'Bid must be at least ₹{min_bid:.2f}.', 'warning')
    else:
        db_execute('INSERT INTO bids (auction_id, bidder_id, amount) VALUES (?, ?, ?)',
                   (auction_id, g.user.id, amount))
        db_commit()
        flash('Bid placed successfully!', 'success')

    return redirect(url_for('auction_detail', auction_id=auction_id))


# ── Seller delete their own auction ──────────────────────────
@app.route('/seller/delete_auction/<int:auction_id>', methods=['POST'])
def seller_delete_auction(auction_id):
    if not g.user or g.user.role not in ('seller', 'admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    auction = db_execute('SELECT * FROM auctions WHERE id = ?', (auction_id,)).fetchone()
    if not auction:
        flash('Auction not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Sellers can only delete their own auctions; admins can delete any
    if g.user.role == 'seller' and auction['seller_id'] != g.user.id:
        flash('You can only delete your own auctions.', 'danger')
        return redirect(url_for('dashboard'))

    db_execute('DELETE FROM bids WHERE auction_id = ?', (auction_id,))
    db_execute('DELETE FROM auctions WHERE id = ?', (auction_id,))
    db_commit()

    flash(f'Auction "{auction["title"]}" deleted successfully.', 'success')
    return redirect(url_for('dashboard'))


# ── Admin panel ───────────────────────────────────────────────
@app.route('/admin-panel')
def admin_panel():
    if not g.user or g.user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    stats = {}
    stats['total_users'] = db_execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    stats['total_auctions'] = db_execute('SELECT COUNT(*) as c FROM auctions').fetchone()['c']
    stats['active_auctions'] = db_execute("SELECT COUNT(*) as c FROM auctions WHERE status = 'live'").fetchone()['c']
    stats['total_bids'] = db_execute('SELECT COUNT(*) as c FROM bids').fetchone()['c']

    users = db_execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()

    auctions = []
    rows = db_execute('''
        SELECT a.*, u.username as seller_name
        FROM auctions a
        JOIN users u ON a.seller_id = u.id
        ORDER BY a.created_at DESC
    ''').fetchall()
    for row in rows:
        bids = db_execute('SELECT COUNT(*) as c, MAX(amount) as m FROM bids WHERE auction_id = ?',
                          (row['id'],)).fetchone()
        auc = dict(row)
        auc['bid_count'] = bids['c'] if bids else 0
        auc['highest_bid'] = bids['m'] if bids['m'] else None
        auctions.append(auc)

    return render_template('admin_panel.html', stats=stats, users=users, auctions=auctions)


@app.route('/admin/delete_auction/<int:auction_id>', methods=['POST'])
def admin_delete_auction(auction_id):
    if not g.user or g.user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    auction = db_execute('SELECT id, title FROM auctions WHERE id = ?', (auction_id,)).fetchone()
    if not auction:
        flash('Auction not found.', 'danger')
        return redirect(url_for('admin_panel'))

    db_execute('DELETE FROM bids WHERE auction_id = ?', (auction_id,))
    db_execute('DELETE FROM auctions WHERE id = ?', (auction_id,))
    db_commit()

    flash(f'Auction "{auction["title"]}" was successfully deleted.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/ban_user/<int:user_id>', methods=['POST'])
def admin_ban_user(user_id):
    if not g.user or g.user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    user = db_execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_panel'))

    new_status = not user['is_banned']
    db_execute('UPDATE users SET is_banned = ? WHERE id = ?', (new_status, user_id))
    db_commit()

    action = 'banned' if new_status else 'unbanned'
    flash(f'User "{user["username"]}" has been {action}.', 'success')
    return redirect(url_for('admin_panel'))


# ─────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        if not _use_postgres():
            # Local SQLite: create db file if missing
            import sqlite3 as _sq
            if not os.path.exists(app.config['DATABASE']):
                os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
        try:
            init_db()
        except Exception as e:
            print(f"Warning: init_db failed: {e}")
    app.run(debug=True)
