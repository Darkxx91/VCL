import sqlite3
from flask import Flask, render_template

# --- Configuration ---
DB_FILE = "leads.db"

app = Flask(__name__)

def get_db_connection():
    """Creates a database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Main dashboard page to display leads."""
    conn = get_db_connection()
    try:
        leads = conn.execute('SELECT * FROM leads ORDER BY scraped_at DESC').fetchall()
    except sqlite3.OperationalError:
        # This can happen if the scraper hasn't run yet and the table doesn't exist.
        leads = []
        print("Warning: 'leads' table not found. Run scraper.py first.")
    conn.close()
    return render_template('index.html', leads=leads)

if __name__ == '__main__':
    # It is recommended to use a proper WSGI server in production
    app.run(debug=True, host='0.0.0.0', port=8080)
