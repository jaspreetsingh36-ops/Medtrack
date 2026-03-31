from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'medtrack-secret-key-2024'

# Database configuration - Update with your Render database URL
DATABASE_URL = "postgresql://medtrack_user:W44bRWWdInicqwFzUYiJJ2bCHwonUeiv@dpg-d73lhs94tr6s73catuog-a.oregon-postgres.render.com/medtrack_db_lq7i"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MedTrack - Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .container {
                background: white;
                border-radius: 10px;
                padding: 40px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                max-width: 400px;
                width: 100%;
            }
            h1 { color: #667eea; text-align: center; }
            .btn {
                display: inline-block;
                padding: 10px 20px;
                margin: 10px 5px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                text-align: center;
            }
            .btn:hover { background: #764ba2; }
            .buttons { text-align: center; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏥 MedTrack</h1>
            <p style="text-align: center;">Medical Records Management System</p>
            <div class="buttons">
                <a href="/login" class="btn">Login</a>
                <a href="/setup" class="btn">Setup Database</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/setup')
def setup():
    """Setup database and create admin user"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) NOT NULL,
                role VARCHAR(20) DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Check if admin exists
        cur.execute("SELECT * FROM users WHERE username = 'admin'")
        admin_exists = cur.fetchone()
        
        if not admin_exists:
            # Create admin user with proper password hash
            admin_hash = generate_password_hash('admin123')
            cur.execute(
                "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                ('admin', admin_hash, 'admin@medtrack.com', 'admin')
            )
            conn.commit()
            message = "✅ Admin user created! Password: admin123"
        else:
            message = "✅ Admin user already exists"
        
        cur.close()
        conn.close()
        
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px; text-align: center;">
            <h1 style="color: green;">{message}</h1>
            <a href="/login" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Login</a>
        </body>
        </html>
        '''
    except Exception as e:
        return f'<h1>Error: {str(e)}</h1>'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user:
                if check_password_hash(user['password'], password):
                    session['user_id'] = user['user_id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid password', 'danger')
            else:
                flash('Username not found', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('login'))
    
    # Show login form
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - MedTrack</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .container {
                background: white;
                border-radius: 10px;
                padding: 40px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                max-width: 400px;
                width: 100%;
            }
            h2 { color: #667eea; text-align: center; }
            input {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            button {
                width: 100%;
                padding: 10px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover { background: #764ba2; }
            .flash {
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                background: #f8d7da;
                color: #721c24;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>MedTrack Login</h2>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
            <p style="text-align: center; margin-top: 20px;">
                <small>Demo: admin / admin123</small>
            </p>
        </div>
    </body>
    </html>
    '''

@app.route('/dashboard')
@login_required
def dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - MedTrack</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f0f2f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 { color: #667eea; }
            .logout {
                background: #dc3545;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
            }
            .logout:hover { background: #c82333; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏥 MedTrack Dashboard</h1>
                <p>Welcome, {{ session.username }}! (Role: {{ session.role }})</p>
                <a href="/logout" class="logout">Logout</a>
            </div>
            <div class="card">
                <h2>✅ Login Successful!</h2>
                <p>Your MedTrack application is working correctly.</p>
                <p>You can now add the full CRUD functionality back.</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)