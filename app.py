import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'super_secret_mindmate_key_123'

# Database Setup
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS counselors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS check_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            vibe TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS triage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            snippet TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            is_unmasked BOOLEAN NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scribbles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_id INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Insert default counselor if it doesn't exist
    cursor.execute("SELECT id FROM counselors WHERE username = 'counselor'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("INSERT INTO counselors (username, password_hash) VALUES (?, ?)", ('counselor', hashed_pw))
        
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/auth')
def auth():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'}), 400

    hashed_password = generate_password_hash(password)

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        # Log them in automatically after signup
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({'success': True, 'message': 'Signup successful'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Username already exists'}), 409
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        session['user_id'] = user[0]
        session['username'] = user[1]
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('counselor_id', None)
    session.pop('counselor_username', None)
    return redirect(url_for('home'))

@app.route('/counselor')
def counselor_home():
    if 'counselor_id' in session:
        return redirect(url_for('counselor_dashboard'))
    return render_template('counselor_login.html')

@app.route('/counselor-login', methods=['POST'])
def counselor_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM counselors WHERE username = ?", (username,))
    counselor = cursor.fetchone()
    conn.close()
    
    if counselor and check_password_hash(counselor[2], password):
        session['counselor_id'] = counselor[0]
        session['counselor_username'] = counselor[1]
        return jsonify({'success': True, 'message': 'Counselor Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid counselor credentials'}), 401

@app.route('/counselor-dashboard')
def counselor_dashboard():
    if 'counselor_id' not in session:
        return redirect(url_for('counselor_home'))
    return render_template('counselor_dashboard.html', username=session.get('counselor_username'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('MINDMATE.html', username=session.get('username'))

@app.route('/api/check_in', methods=['POST'])
def check_in():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    vibe = data.get('vibe', 'vent') # default to vent if no specific vibe
    
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    user_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if already logged today
    cursor.execute("SELECT id, vibe FROM check_ins WHERE user_id = ? AND date = ?", (user_id, today))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("UPDATE check_ins SET vibe = ? WHERE id = ?", (vibe, existing[0]))
    else:
        cursor.execute("INSERT INTO check_ins (user_id, date, vibe) VALUES (?, ?, ?)", (user_id, today, vibe))
        
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/insights')
def get_insights():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    user_id = session['user_id']
    from datetime import datetime
    import calendar
    
    now = datetime.now()
    year, month = now.year, now.month
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT date, vibe FROM check_ins WHERE user_id = ? AND date LIKE ?", (user_id, f"{year}-{month:02d}-%"))
    records = cursor.fetchall()
    conn.close()
    
    check_ins = {r[0]: r[1] for r in records}
    
    num_days = calendar.monthrange(year, month)[1]
    
    return jsonify({
        'success': True,
        'month': now.strftime('%B %Y'),
        'num_days': num_days,
        'check_ins': check_ins
    })

@app.route('/api/log_triage', methods=['POST'])
def log_triage():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    snippet = data.get('snippet')
    risk_level = data.get('risk_level', 'moderate')
    is_unmasked = data.get('is_unmasked', False)
    
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO triage_logs (user_id, snippet, risk_level, is_unmasked, timestamp, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, snippet, risk_level, is_unmasked, timestamp, 'pending'))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/counselor/queue', methods=['GET'])
def counselor_queue():
    if 'counselor_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.user_id, t.snippet, t.risk_level, t.is_unmasked, t.timestamp, u.username
        FROM triage_logs t
        JOIN users u ON t.user_id = u.id
        WHERE t.status = 'pending'
        ORDER BY t.timestamp ASC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    queue = []
    for r in rows:
        queue.append({
            'id': r[0],
            'user_id': r[1],
            'snippet': r[2],
            'risk_level': r[3],
            'is_unmasked': bool(r[4]),
            'timestamp': r[5],
            'username': r[6]
        })
        
    return jsonify({'success': True, 'queue': queue})

@app.route('/api/counselor/action', methods=['POST'])
def counselor_action():
    if 'counselor_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    log_id = data.get('id')
    action = data.get('action') # 'approved', 'ignored', or 'dispatched_*'
    
    if not log_id or action not in ['approved', 'ignored', 'dispatched_police', 'dispatched_medics', 'dispatched_security']:
        return jsonify({'success': False}), 400
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE triage_logs SET status = ? WHERE id = ?", (action, log_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/counselor/stats', methods=['GET'])
def counselor_stats():
    if 'counselor_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM triage_logs WHERE status = 'approved'")
    solved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM triage_logs WHERE status = 'ignored'")
    declined = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM triage_logs WHERE status LIKE 'dispatched_%'")
    dispatched = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({'success': True, 'solved': solved, 'declined': declined, 'dispatched': dispatched})

@app.route('/api/scribbles', methods=['GET'])
def get_scribbles():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, timestamp, user_id FROM scribbles ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    
    scribbles = []
    for r in rows:
        scribbles.append({
            'id': r[0],
            'content': r[1],
            'timestamp': r[2],
            'is_mine': (r[3] == session.get('user_id'))
        })
    return jsonify({'success': True, 'scribbles': scribbles})

@app.route('/api/scribbles', methods=['POST'])
def post_scribble():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.get_json()
    content = data.get('content')
    if not content:
        return jsonify({'success': False, 'message': 'Content required'}), 400
        
    from datetime import datetime
    timestamp = datetime.now().strftime('%I:%M %p')
    user_id = session.get('user_id')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scribbles (content, timestamp, user_id) VALUES (?, ?, ?)", (content, timestamp, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/scribbles/<int:scribble_id>', methods=['DELETE'])
def delete_scribble(scribble_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    user_id = session.get('user_id')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM scribbles WHERE id = ?", (scribble_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'Not found'}), 404
        
    if row[0] != user_id:
        conn.close()
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
    cursor.execute("DELETE FROM scribbles WHERE id = ?", (scribble_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/chat/send', methods=['POST'])
def send_chat():
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'success': False, 'message': 'Message required'}), 400
        
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    user_id = None
    sender_type = None
    
    if 'user_id' in session:
        user_id = session['user_id']
        sender_type = 'user'
    elif 'counselor_id' in session:
        user_id = data.get('user_id') # Counselor must specify which user they are messaging
        sender_type = 'counselor'
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required for counselor'}), 400
    else:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (user_id, sender_type, message, timestamp) VALUES (?, ?, ?, ?)", 
                   (user_id, sender_type, message, timestamp))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/chat/messages', methods=['GET'])
def get_chat_messages():
    user_id = None
    if 'user_id' in session:
        user_id = session['user_id']
    elif 'counselor_id' in session:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
    else:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender_type, message, timestamp FROM chats WHERE user_id = ? ORDER BY id ASC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    messages = []
    for r in rows:
        messages.append({
            'id': r[0],
            'sender_type': r[1],
            'message': r[2],
            'timestamp': r[3]
        })
        
    return jsonify({'success': True, 'messages': messages})

@app.route('/api/counselor/active_chats', methods=['GET'])
def get_active_chats():
    if 'counselor_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get distinct users who have chats
    cursor.execute('''
        SELECT DISTINCT c.user_id 
        FROM chats c
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # Anonymize the username
    active_chats = [{'user_id': r[0], 'username': f"Anonymous Student #{r[0]}"} for r in rows]
    return jsonify({'success': True, 'active_chats': active_chats})

if __name__ == '__main__':
    app.run(debug=True, port=3000)
