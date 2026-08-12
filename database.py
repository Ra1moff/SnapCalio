import os
import sqlite3
from datetime import datetime, timezone, timedelta

# Database file path
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'snapcal.db')

# Timezone helper: Tashkent is UTC+5
TASHKENT_TZ = timezone(timedelta(hours=5))

def get_tashkent_time():
    """Returns current datetime in Tashkent time (UTC+5)."""
    return datetime.now(TASHKENT_TZ)

def get_connection():
    """Returns a connection to the SQLite database, creating the directory if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initializes the database and creates tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table for food scans
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            calories REAL DEFAULT 0.0,
            protein REAL DEFAULT 0.0,
            carbs REAL DEFAULT 0.0,
            fat REAL DEFAULT 0.0,
            description TEXT,
            timestamp TEXT NOT NULL  -- Format: 'YYYY-MM-DD HH:MM:SS'
        )
    ''')
    
    conn.commit()
    conn.close()

def save_scan(user_id, food_name, calories, protein, carbs, fat, description):
    """Saves a food scan entry to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Store timestamp as Tashkent local time
    timestamp_str = get_tashkent_time().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO scans (user_id, food_name, calories, protein, carbs, fat, description, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, food_name, calories, protein, carbs, fat, description, timestamp_str))
    
    conn.commit()
    scan_id = cursor.lastrowid
    conn.close()
    return scan_id

def get_user_scans(user_id, limit=20, offset=0):
    """Retrieves list of scans for a specific user, sorted by timestamp descending."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, food_name, calories, protein, carbs, fat, description, timestamp
        FROM scans
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    ''', (user_id, limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_daily_summary(user_id, date_str=None):
    """
    Returns the list of scans and total nutritional values for a specific day.
    date_str format: 'YYYY-MM-DD'. If None, defaults to Tashkent today's date.
    """
    if not date_str:
        date_str = get_tashkent_time().strftime('%Y-%m-%d')
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all scans for this day (comparing just the date part of timestamp)
    cursor.execute('''
        SELECT id, food_name, calories, protein, carbs, fat, description, timestamp
        FROM scans
        WHERE user_id = ? AND date(timestamp) = date(?)
        ORDER BY timestamp ASC
    ''', (user_id, date_str))
    
    rows = cursor.fetchall()
    scans = [dict(row) for row in rows]
    
    # Calculate totals
    cursor.execute('''
        SELECT 
            COALESCE(SUM(calories), 0) as total_calories,
            COALESCE(SUM(protein), 0) as total_protein,
            COALESCE(SUM(carbs), 0) as total_carbs,
            COALESCE(SUM(fat), 0) as total_fat
        FROM scans
        WHERE user_id = ? AND date(timestamp) = date(?)
    ''', (user_id, date_str))
    
    totals = dict(cursor.fetchone())
    conn.close()
    
    # Parse timestamp to get Uzbek day names and times
    weekdays_uz = {
        0: 'Dushanba',
        1: 'Seshanba',
        2: 'Chorshanba',
        3: 'Payshanba',
        4: 'Juma',
        5: 'Shanba',
        6: 'Yakshanba'
    }
    
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_of_week = weekdays_uz[dt.weekday()]
    
    return {
        'date': date_str,
        'day_of_week': day_of_week,
        'scans': scans,
        'totals': totals
    }

def clear_user_history(user_id):
    """Clears scan history for a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM scans WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
