import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from reddit_lead_finder.scraper import run_scraper # Import the scraper function

# --- Configuration ---
DB_FILE = "leads.db"
SECRET_KEY = os.urandom(24)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'])
    return None

def get_db_connection():
    """Creates a database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Sets up the database tables for leads and users."""
    conn = get_db_connection()
    c = conn.cursor()
    # Leads table
    c.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY, title TEXT, score INTEGER, subreddit TEXT,
            url TEXT, created_utc REAL, body TEXT, scraped_at TEXT
        )
    ''')
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("Database tables for leads and users are ready.")


@app.route('/')
@login_required
def index():
    """Main dashboard page to display leads."""
    conn = get_db_connection()
    leads = conn.execute('SELECT * FROM leads ORDER BY scraped_at DESC').fetchall()
    conn.close()
    return render_template('index.html', leads=leads)

@app.route('/run-scraper', methods=['POST'])
@login_required
def trigger_scraper():
    """Triggers the Reddit scraper to run."""
    flash("Scraping started... This may take a few minutes.", "info")
    result = run_scraper()
    if result.get('status') == 'success':
        flash(f"Scraping complete! Found {result.get('leads_found', 0)} new leads.", "success")
    else:
        flash(f"Scraping failed: {result.get('message', 'Unknown error')}", "error")
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user_data and check_password_hash(user_data['password'], password):
            user = User(id=user_data['id'], username=user_data['username'])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Set up the database immediately when the app is initialized.
setup_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
