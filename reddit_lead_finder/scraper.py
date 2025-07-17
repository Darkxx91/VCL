import praw
import os

# --- Configuration ---
# It's recommended to use environment variables for credentials in a real application
# For now, we'll use placeholders. The user will need to provide their own credentials.
CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "YOUR_CLIENT_ID")
CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "YOUR_USER_AGENT")

import time
import openai
import sqlite3
from datetime import datetime

# --- Database Configuration ---
DB_FILE = "leads.db"

# --- Configuration ---
# It's recommended to use environment variables for credentials in a real application
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize OpenAI client
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Subreddits to monitor for leads
TARGET_SUBREDDITS = ["saas", "marketing", "sales", "startups", "smallbusiness"]

def setup_database():
    """Sets up the SQLite database and creates the leads table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            title TEXT,
            score INTEGER,
            subreddit TEXT,
            url TEXT,
            created_utc REAL,
            body TEXT,
            scraped_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Database setup complete.")

def save_lead(post):
    """Saves a lead to the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO leads (id, title, score, subreddit, url, created_utc, body, scraped_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (post.id, post.title, post.score, post.subreddit.display_name, post.shortlink, post.created_utc, post.selftext, datetime.utcnow().isoformat()))
        conn.commit()
        print(f"    [DB] Saved lead: '{post.title[:50]}...'")
    except sqlite3.IntegrityError:
        # This means the lead (post.id) already exists in the database.
        print(f"    [DB] Lead '{post.title[:50]}...' already exists. Skipping.")
    except Exception as e:
        print(f"    [DB ERROR] Could not save lead. Error: {e}")
    finally:
        conn.close()

def is_lead_material(post_title, post_body):
    """
    Analyzes post content using OpenAI to determine if it's a potential B2B lead.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
        print("    [AI SIM] OpenAI key not found. Simulating lead check.")
        # Fallback to simple keyword check if API key is not available
        lead_keywords = ["looking for", "recommendation", "how to", "software for", "tool for", "help with", "alternative to"]
        text_to_analyze = (post_title + " " + post_body).lower()
        return any(keyword in text_to_analyze for keyword in lead_keywords)

    try:
        prompt = f"""
        Analyze the following Reddit post to determine if it represents a B2B sales lead.
        The post should be from someone looking for a tool, software, or service for their business.
        Ignore posts about job seeking, hiring, or general news.

        Post Title: {post_title}
        Post Body: {post_body}

        Is this a potential B2B sales lead? Respond with only "Yes" or "No".
        """

        # Using the newer client syntax for OpenAI
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that identifies B2B sales leads."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=5,
            temperature=0.1,
        )

        answer = response.choices[0].message.content.strip()
        print(f"    [AI] Analysis for '{post_title[:50]}...': {answer}")
        return "yes" in answer.lower()

    except Exception as e:
        print(f"    [AI ERROR] Could not analyze post with OpenAI. Error: {e}")
        return False


def initialize_reddit():
    """Initializes and returns a PRAW Reddit instance."""
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT,
    )
    # Set to read-only mode if you don't need to log in as a user
    reddit.read_only = True
    return reddit

def fetch_hot_posts(reddit, subreddit_name, limit=10):
    """
    Fetches the top 'limit' hot posts from a given subreddit.

    Args:
        reddit: An initialized PRAW Reddit instance.
        subreddit_name: The name of the subreddit to fetch posts from.
        limit: The number of posts to fetch.

    Returns:
        A list of PRAW Submission objects (posts).
    """
    try:
        subreddit = reddit.subreddit(subreddit_name)
        hot_posts = list(subreddit.hot(limit=limit))
        print(f"Successfully fetched {len(hot_posts)} posts from r/{subreddit_name}.")
        return hot_posts
    except Exception as e:
        print(f"Could not fetch posts from r/{subreddit_name}. Error: {e}")
        return []

def run_scraper():
    """The main logic for scraping and analyzing Reddit posts."""
    print("--- Running Scraper ---")

    # Check for credentials at the start of the run
    if CLIENT_ID == "YOUR_CLIENT_ID" or CLIENT_SECRET == "YOUR_CLIENT_SECRET":
        print("ERROR: Reddit API credentials are not configured.")
        return {"status": "error", "message": "Reddit API credentials not set."}

    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
        print("WARNING: OpenAI API key not set. AI analysis will be simulated.")

    reddit = initialize_reddit()
    leads_found = 0

    print("--- Starting Lead Search ---")
    for subreddit_name in TARGET_SUBREDDITS:
        posts = fetch_hot_posts(reddit, subreddit_name, limit=10) # Increased limit slightly
        if posts:
            print(f"Analyzing posts in r/{subreddit_name}:")
            for post in posts:
                post_body = post.selftext if hasattr(post, 'selftext') else ""
                if is_lead_material(post.title, post_body):
                    save_lead(post)
                    leads_found += 1
                time.sleep(0.5) # API courtesy delay

    print(f"--- Scraper finished. Found {leads_found} new leads. ---")
    return {"status": "success", "leads_found": leads_found}


def main():
    """Main function to run the scraper from the command line."""
    print("Initializing Reddit scraper for command-line execution...")
    setup_database()
    run_scraper()


if __name__ == "__main__":
    main()
