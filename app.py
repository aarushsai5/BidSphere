from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Ensure database directory exists
if not os.environ.get('VERCEL'):
    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db_path = app.config['DATABASE']
        if os.environ.get('VERCEL'):
            db_path = '/tmp/auction.db'
            if not os.path.exists(db_path):
                import shutil
                try:
                    shutil.copy2(app.config['DATABASE'], db_path)
                except Exception:
                    pass
        db = g._database = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('database/schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

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
        db = get_db()
        row = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if row:
            g.user = User(id=row['id'], username=row['username'], email=row['email'], role=row['role'])
        else:
            g.user = None

@app.context_processor
def inject_user():
    return dict(current_user=g.user)

@app.template_filter('format_ist')
def format_ist(value):
    # Stub for format_ist since it's used in templates
    return value

@app.route('/')
def index():
    db = get_db()
    
    status_filter = request.args.get('status', 'all')
    search = request.args.get('q', '')

    query = 'SELECT * FROM auctions WHERE 1=1'
    params = []
    
    if status_filter != 'all':
        query += ' AND status = ?'
        params.append(status_filter)
    if search:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    auctions_rows = db.execute(query, params).fetchall()
    
    # We map row to dict to inject seller_name
    auctions = []
    for row in auctions_rows:
        seller = db.execute('SELECT username FROM users WHERE id = ?', (row['seller_id'],)).fetchone()
        bids = db.execute('SELECT COUNT(*) as c, MAX(amount) as m FROM bids WHERE auction_id = ?', (row['id'],)).fetchone()
        
        auc = dict(row)
        auc['seller_name'] = seller['username'] if seller else 'Unknown'
        auc['bid_count'] = bids['c'] if bids else 0
        auc['highest_bid'] = bids['m'] if bids['m'] else None
        auctions.append(auc)

    return render_template('index.html', auctions=auctions, status_filter=status_filter, search=search)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()
        
        # Allow login by username or email
        user = db.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username)).fetchone()
        
        if user is None:
            print(f"Login debug: User not found for {username}")
            flash('Incorrect username or email.', 'danger')
        elif not check_password_hash(str(user['password']), password):
            print(f"Login debug: Password check failed for {username}")
            flash('Incorrect password.', 'danger')
        elif user['is_banned']:
            print(f"Login debug: User {username} is banned")
            flash('This account is banned.', 'danger')
        else:
            print(f"Login debug: Success for {username}")
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
        
        db = get_db()
        error = None
        
        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"User {username} is already registered."
        elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone() is not None:
            error = f"Email {email} is already registered."
            
        if error is None:
            db.execute(
                'INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                (username, email, generate_password_hash(password), role)
            )
            db.commit()
            
            # Auto login after register
            user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
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
        
        image_file = request.files.get('image')
        filename = ''
        if image_file and image_file.filename:
            import werkzeug.utils
            filename = werkzeug.utils.secure_filename(image_file.filename)
            upload_path = app.config['UPLOAD_FOLDER']
            if os.environ.get('VERCEL'):
                upload_path = '/tmp'
            image_file.save(os.path.join(upload_path, filename))
            
        if not start_time:
            from datetime import datetime
            start_time = datetime.now().strftime('%Y-%m-%dT%H:%M')
            
        db = get_db()
        db.execute(
            'INSERT INTO auctions (seller_id, title, description, image, starting_price, min_increment, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, "live")',
            (g.user.id, title, full_desc, filename, starting_price, min_increment, start_time, end_time)
        )
        db.commit()

        flash('Auction created successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('create_auction.html')

@app.route('/dashboard')
def dashboard():
    if not g.user:
        flash('Please login to view your dashboard.', 'danger')
        return redirect(url_for('login'))
        
    db = get_db()
    auctions = []
    
    if g.user.role in ('seller', 'admin'):
        # Show seller's listings
        rows = db.execute('SELECT * FROM auctions WHERE seller_id = ? ORDER BY created_at DESC', (g.user.id,)).fetchall()
        for row in rows:
            bids = db.execute('SELECT COUNT(*) as c, MAX(amount) as m FROM bids WHERE auction_id = ?', (row['id'],)).fetchone()
            auc = dict(row)
            auc['bid_count'] = bids['c'] if bids else 0
            auc['highest_bid'] = bids['m'] if bids['m'] else None
            auctions.append(auc)
    else:
        # Show bidder's active bids
        query = '''
            SELECT DISTINCT a.* FROM auctions a
            JOIN bids b ON a.id = b.auction_id
            WHERE b.bidder_id = ? ORDER BY b.created_at DESC
        '''
        rows = db.execute(query, (g.user.id,)).fetchall()
        for row in rows:
            bids = db.execute('SELECT MAX(amount) as m FROM bids WHERE auction_id = ?', (row['id'],)).fetchone()
            user_bid = db.execute('SELECT MAX(amount) as m FROM bids WHERE auction_id = ? AND bidder_id = ?', (row['id'], g.user.id)).fetchone()
            auc = dict(row)
            auc['highest_bid'] = bids['m'] if bids['m'] else None
            auc['my_bid'] = user_bid['m'] if user_bid['m'] else None
            # Check if user is currently winning
            auc['is_winning'] = auc['highest_bid'] == auc['my_bid']
            auctions.append(auc)
            
    return render_template('dashboard.html', auctions=auctions)

@app.route('/auction/<int:auction_id>')
def auction_detail(auction_id):
    db = get_db()
    row = db.execute('SELECT * FROM auctions WHERE id = ?', (auction_id,)).fetchone()
    if not row:
        flash('Auction not found.', 'danger')
        return redirect(url_for('index'))
        
    auction = dict(row)
    seller = db.execute('SELECT username FROM users WHERE id = ?', (auction['seller_id'],)).fetchone()
    auction['seller_name'] = seller['username'] if seller else 'Unknown'
    
    # Get current bids
    bids = db.execute('''
        SELECT b.amount, b.created_at, u.username as bidder_name 
        FROM bids b
        JOIN users u ON b.bidder_id = u.id
        WHERE b.auction_id = ? 
        ORDER BY b.amount DESC
    ''', (auction_id,)).fetchall()
    
    current_bid = bids[0]['amount'] if bids else auction['starting_price']
    
    return render_template('auction_detail.html', auction=auction, bids=bids, current_bid=current_bid)

@app.route('/auction/<int:auction_id>/bid', methods=['POST'])
def place_bid(auction_id):
    if not g.user:
        flash('You must be logged in to place a bid.', 'danger')
        return redirect(url_for('login'))
        
    if g.user.role == 'seller':
        flash('Sellers cannot place bids.', 'danger')
        return redirect(url_for('index'))
        
    amount = float(request.form.get('amount', 0))
    db = get_db()
    
    # Verify auction exists and is live
    auction = db.execute('SELECT * FROM auctions WHERE id = ?', (auction_id,)).fetchone()
    if not auction:
        flash('Auction not found.', 'danger')
        return redirect(url_for('index'))
        
    if auction['status'] != 'live':
        flash('This auction is not currently active.', 'danger')
        return redirect(url_for('auction_detail', auction_id=auction_id))
        
    # Check current highest bid
    highest = db.execute('SELECT MAX(amount) as m FROM bids WHERE auction_id = ?', (auction_id,)).fetchone()
    current_highest = highest['m'] if highest['m'] else auction['starting_price']
    
    min_bid = current_highest + auction['min_increment']
    if amount < min_bid:
        flash(f'Bid must be at least ₹{min_bid:.2f}.', 'warning')
    else:
        db.execute('INSERT INTO bids (auction_id, bidder_id, amount) VALUES (?, ?, ?)',
                  (auction_id, g.user.id, amount))
        db.commit()
        flash('Bid placed successfully!', 'success')
        
    return redirect(url_for('auction_detail', auction_id=auction_id))

@app.route('/admin-panel')
def admin_panel():
    if not g.user or g.user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
        
    db = get_db()
    
    # Get platform statistics
    stats = {}
    stats['total_users'] = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    stats['total_auctions'] = db.execute('SELECT COUNT(*) as c FROM auctions').fetchone()['c']
    stats['active_auctions'] = db.execute('SELECT COUNT(*) as c FROM auctions WHERE status = "live"').fetchone()['c']
    stats['total_bids'] = db.execute('SELECT COUNT(*) as c FROM bids').fetchone()['c']
    
    # Get users list
    users = db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    
    # Get auctions list
    auctions = []
    rows = db.execute('''
        SELECT a.*, u.username as seller_name 
        FROM auctions a 
        JOIN users u ON a.seller_id = u.id 
        ORDER BY a.created_at DESC
    ''').fetchall()
    
    for row in rows:
        bids = db.execute('SELECT COUNT(*) as c, MAX(amount) as m FROM bids WHERE auction_id = ?', (row['id'],)).fetchone()
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
        
    db = get_db()
    auction = db.execute('SELECT id, title FROM auctions WHERE id = ?', (auction_id,)).fetchone()
    
    if not auction:
        flash('Auction not found.', 'danger')
        return redirect(url_for('admin_panel'))
        
    # Delete associated bids first
    db.execute('DELETE FROM bids WHERE auction_id = ?', (auction_id,))
    # Delete the auction
    db.execute('DELETE FROM auctions WHERE id = ?', (auction_id,))
    db.commit()
    
    flash(f'Auction "{auction["title"]}" was successfully deleted.', 'success')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    app.run(debug=True)
