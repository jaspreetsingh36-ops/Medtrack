from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import Config
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os
import traceback

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'medtrack-secret-key-2024'

def get_db_connection():
    return psycopg2.connect(app.config['DATABASE_URL'])

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
    return render_template('index.html')

@app.route('/init-db')
def init_database_route():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Drop and recreate tables
        cur.execute("DROP TABLE IF EXISTS prescriptions CASCADE")
        cur.execute("DROP TABLE IF EXISTS clinical_visits CASCADE")
        cur.execute("DROP TABLE IF EXISTS appointments CASCADE")
        cur.execute("DROP TABLE IF EXISTS staff CASCADE")
        cur.execute("DROP TABLE IF EXISTS doctors CASCADE")
        cur.execute("DROP TABLE IF EXISTS patients CASCADE")
        cur.execute("DROP TABLE IF EXISTS users CASCADE")
        
        # Create users table
        cur.execute("""
            CREATE TABLE users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) NOT NULL,
                role VARCHAR(20) DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create patients table
        cur.execute("""
            CREATE TABLE patients (
                patient_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                dob DATE,
                contact VARCHAR(20),
                insurance_no VARCHAR(50),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create doctors table
        cur.execute("""
            CREATE TABLE doctors (
                doctor_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                name VARCHAR(100) NOT NULL,
                specialization VARCHAR(100),
                contact VARCHAR(20),
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create appointments table
        cur.execute("""
            CREATE TABLE appointments (
                appointment_id SERIAL PRIMARY KEY,
                patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
                doctor_id INTEGER NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                appointment_date TIMESTAMP NOT NULL,
                status VARCHAR(20) DEFAULT 'scheduled',
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create clinical_visits table
        cur.execute("""
            CREATE TABLE clinical_visits (
                visit_id SERIAL PRIMARY KEY,
                patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
                doctor_id INTEGER NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                visit_date TIMESTAMP NOT NULL,
                symptoms TEXT,
                diagnosis TEXT,
                treatment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create prescriptions table
        cur.execute("""
            CREATE TABLE prescriptions (
                prescription_id SERIAL PRIMARY KEY,
                visit_id INTEGER NOT NULL REFERENCES clinical_visits(visit_id) ON DELETE CASCADE,
                medicine_name VARCHAR(100) NOT NULL,
                dosage VARCHAR(100),
                duration VARCHAR(100),
                instructions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        
        # Create users with proper password hashes
        admin_hash = generate_password_hash('admin123')
        staff_hash = generate_password_hash('staff123')
        doctor_hash = generate_password_hash('doctor123')
        
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('admin', admin_hash, 'admin@medtrack.com', 'admin'))
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('staff_jane', staff_hash, 'jane@medtrack.com', 'staff'))
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('dr_smith', doctor_hash, 'sarah.smith@medtrack.com', 'doctor'))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return """
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h1 style="color: green;">✅ Database Initialized!</h1>
            <p>Users created:</p>
            <ul>
                <li>admin / admin123 (Admin)</li>
                <li>staff_jane / staff123 (Staff)</li>
                <li>dr_smith / doctor123 (Doctor)</li>
            </ul>
            <a href="/login" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Login</a>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1><pre>{traceback.format_exc()}</pre>"

@app.route('/check-users')
def check_users():
    """Debug route to see users in database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT user_id, username, role, password FROM users")
        users = cur.fetchall()
        cur.close()
        conn.close()
        
        html = "<h1>Users in Database</h1>"
        html += "<table border='1' cellpadding='10'>"
        html += "<tr><th>ID</th><th>Username</th><th>Role</th><th>Password Hash (first 50 chars)</th></tr>"
        for user in users:
            html += f"<tr><td>{user['user_id']}</td><td>{user['username']}</td><td>{user['role']}</td><td>{user['password'][:50]}...</td></tr>"
        html += "</table>"
        html += '<br><a href="/login">Back to Login</a>'
        return html
    except Exception as e:
        return f"Error: {str(e)}"

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
                # Check password
                if check_password_hash(user['password'], password):
                    session['user_id'] = user['user_id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    flash(f'Welcome {username}!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid password', 'danger')
            else:
                flash('Username not found', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', 
                         patient_count=0,
                         doctor_count=0,
                         appointment_count=0,
                         visit_count=0,
                         recent_appointments=[])

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)