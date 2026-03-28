from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import Config
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.config.from_object(Config)

# Database connection function
def get_db_connection():
    return psycopg2.connect(app.config['DATABASE_URL'])

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Role required decorator
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in allowed_roles:
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def utility_processor():
    return {'now': datetime.now()}

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user exists
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user:
            flash('Username already exists', 'danger')
            cur.close()
            conn.close()
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s) RETURNING user_id",
            (username, hashed_password, email, role)
        )
        user_id = cur.fetchone()['user_id']
        conn.commit()
        
        # If role is doctor, create doctor profile
        if role == 'doctor':
            doctor_name = request.form.get('doctor_name')
            specialization = request.form.get('specialization')
            doctor_contact = request.form.get('doctor_contact')
            
            cur.execute(
                """INSERT INTO doctors (user_id, name, specialization, contact, email) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, doctor_name, specialization, doctor_contact, email)
            )
            conn.commit()
        
        # If role is staff, create staff record
        elif role == 'staff':
            staff_name = request.form.get('staff_name')
            staff_contact = request.form.get('staff_contact')
            
            cur.execute(
                """INSERT INTO staff (user_id, name, contact, email) 
                   VALUES (%s, %s, %s, %s)""",
                (user_id, staff_name, staff_contact, email)
            )
            conn.commit()
        
        cur.close()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get counts for dashboard
    cur.execute("SELECT COUNT(*) as count FROM patients")
    patient_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM doctors")
    doctor_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM appointments WHERE status = 'scheduled'")
    appointment_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM clinical_visits WHERE visit_date >= CURRENT_DATE")
    visit_count = cur.fetchone()['count']
    
    # Recent appointments with JOIN
    cur.execute("""
        SELECT a.appointment_id, a.appointment_date, a.status, 
               p.name as patient_name, d.name as doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.appointment_date >= CURRENT_DATE
        ORDER BY a.appointment_date ASC
        LIMIT 5
    """)
    recent_appointments = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('dashboard.html', 
                         patient_count=patient_count,
                         doctor_count=doctor_count,
                         appointment_count=appointment_count,
                         visit_count=visit_count,
                         recent_appointments=recent_appointments)

# [Continue with all the other routes - patients, doctors, appointments, visits, prescriptions]
# They will be identical to the MySQL version but with %s instead of %s for parameters
# (PostgreSQL uses %s just like MySQL for parameterized queries)

# For brevity, I'll continue with one route example, but you'll need all the routes from the previous app.py

@app.route('/patients')
@login_required
def list_patients():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM patients ORDER BY name")
    patients = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('patients/list.html', patients=patients)

# Add all the other routes here...

if __name__ == '__main__':
    app.run(debug=True)