from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'medtrack-secret-key-2024'

# Database configuration
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

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in allowed_roles:
                flash('You do not have permission', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def utility_processor():
    return {'now': datetime.now()}

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MedTrack - Medical Records System</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
            .container { background: white; border-radius: 10px; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); max-width: 500px; text-align: center; }
            h1 { color: #667eea; }
            .btn { display: inline-block; padding: 10px 20px; margin: 10px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }
            .btn:hover { background: #764ba2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏥 MedTrack</h1>
            <p>Medical Records Management System</p>
            <a href="/login" class="btn">Login</a>
            <a href="/setup" class="btn">Setup</a>
        </div>
    </body>
    </html>
    '''

@app.route('/setup')
def setup():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create all tables
        cur.execute("DROP TABLE IF EXISTS prescriptions CASCADE")
        cur.execute("DROP TABLE IF EXISTS clinical_visits CASCADE")
        cur.execute("DROP TABLE IF EXISTS appointments CASCADE")
        cur.execute("DROP TABLE IF EXISTS staff CASCADE")
        cur.execute("DROP TABLE IF EXISTS doctors CASCADE")
        cur.execute("DROP TABLE IF EXISTS patients CASCADE")
        cur.execute("DROP TABLE IF EXISTS users CASCADE")
        
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
        
        # Create users
        admin_hash = generate_password_hash('admin123')
        staff_hash = generate_password_hash('staff123')
        doctor_hash = generate_password_hash('doctor123')
        
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('admin', admin_hash, 'admin@medtrack.com', 'admin'))
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('staff_jane', staff_hash, 'jane@medtrack.com', 'staff'))
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('dr_smith', doctor_hash, 'smith@medtrack.com', 'doctor'))
        conn.commit()
        
        # Get user IDs and create doctor profiles
        cur.execute("SELECT user_id FROM users WHERE username = 'dr_smith'")
        dr_id = cur.fetchone()[0]
        cur.execute("INSERT INTO doctors (user_id, name, specialization, contact, email) VALUES (%s, %s, %s, %s, %s)",
                    (dr_id, 'Dr. Sarah Smith', 'Cardiology', '555-0201', 'sarah.smith@medtrack.com'))
        
        # Add sample patients
        cur.execute("""
            INSERT INTO patients (name, dob, contact, insurance_no, address) VALUES 
            ('John Doe', '1985-03-15', '555-0101', 'INS001', '123 Main St, Toronto'),
            ('Jane Smith', '1990-07-22', '555-0102', 'INS002', '456 Oak Ave, Vancouver'),
            ('Bob Wilson', '1978-11-30', '555-0103', 'INS003', '789 Pine St, Montreal')
        """)
        
        # Add appointments with JOIN data
        cur.execute("""
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, reason) VALUES 
            (1, 1, '2026-04-01 10:00:00', 'scheduled', 'Chest pain'),
            (2, 1, '2026-04-02 14:30:00', 'scheduled', 'Routine checkup'),
            (3, 1, '2026-04-03 11:00:00', 'completed', 'Fever')
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        return '<h1 style="color:green">✅ Database Setup Complete!</h1><a href="/login">Go to Login</a>'
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
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash(f'Welcome {username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('login'))
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - MedTrack</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
            .container { background: white; border-radius: 10px; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }
            h2 { color: #667eea; text-align: center; }
            input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { width: 100%; padding: 10px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #764ba2; }
            .flash { padding: 10px; margin: 10px 0; border-radius: 5px; background: #f8d7da; color: #721c24; }
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
            <p style="text-align:center; margin-top:20px"><small>admin / admin123 | staff_jane / staff123 | dr_smith / doctor123</small></p>
        </div>
    </body>
    </html>
    '''

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get counts
    cur.execute("SELECT COUNT(*) as count FROM patients")
    patient_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM doctors")
    doctor_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM appointments WHERE status = 'scheduled'")
    appointment_count = cur.fetchone()['count']
    
    # Recent appointments with JOIN
    cur.execute("""
        SELECT a.appointment_id, a.appointment_date, a.status, a.reason,
               p.name as patient_name, d.name as doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        ORDER BY a.appointment_date DESC
        LIMIT 5
    """)
    appointments = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - MedTrack</title>
        <style>
            body {{ font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; }}
            .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }}
            .btn-danger {{ background: #dc3545; }}
            .btn-success {{ background: #28a745; }}
            .btn-warning {{ background: #ffc107; color: black; }}
            .logout {{ background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            h1, h2 {{ color: #667eea; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>🏥 MedTrack</h1>
                    <p>Welcome, {session['username']}! (Role: {session['role']})</p>
                </div>
                <div>
                    <a href="/patients" class="btn">Patients</a>
                    <a href="/doctors" class="btn">Doctors</a>
                    <a href="/appointments" class="btn">Appointments</a>
                    <a href="/visits" class="btn">Visits</a>
                    <a href="/logout" class="logout">Logout</a>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{patient_count}</div>
                    <div>Total Patients</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{doctor_count}</div>
                    <div>Total Doctors</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{appointment_count}</div>
                    <div>Upcoming Appointments</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">0</div>
                    <div>Visits This Month</div>
                </div>
            </div>
            
            <div class="card">
                <h2>Recent Appointments (JOIN Query Example)</h2>
                <table>
                    <thead>
                        <tr><th>Date</th><th>Patient</th><th>Doctor</th><th>Status</th><th>Reason</th></tr>
                    </thead>
                    <tbody>
                        {''.join([f'<tr><td>{a["appointment_date"]}</td><td>{a["patient_name"]}</td><td>{a["doctor_name"]}</td><td>{a["status"]}</td><td>{a["reason"] or "N/A"}</td></tr>' for a in appointments])}
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h2>Quick Actions</h2>
                <a href="/patients/add" class="btn btn-success">➕ Add Patient</a>
                <a href="/appointments/add" class="btn">📅 Schedule Appointment</a>
                <a href="/visits/add" class="btn btn-warning">📝 Record Visit</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/patients')
@login_required
def list_patients():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM patients ORDER BY name")
    patients = cur.fetchall()
    cur.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Patients - MedTrack</title>
        <style>
            body {{ font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; }}
            .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }}
            .btn-danger {{ background: #dc3545; }}
            .btn-sm {{ padding: 5px 10px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>👥 Patient Management</h1>
                <div>
                    <a href="/dashboard" class="btn">Back to Dashboard</a>
                    <a href="/patients/add" class="btn">+ Add Patient</a>
                    <a href="/logout" class="btn btn-danger">Logout</a>
                </div>
            </div>
            <div class="card">
                <table>
                    <thead>
                        <tr><th>ID</th><th>Name</th><th>DOB</th><th>Contact</th><th>Insurance</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        {''.join([f'<tr><td>{p["patient_id"]}</td><td>{p["name"]}</td><td>{p["dob"] or "N/A"}</td><td>{p["contact"] or "N/A"}</td><td>{p["insurance_no"] or "N/A"}</td><td><a href="/patients/edit/{p["patient_id"]}" class="btn btn-sm">Edit</a> <a href="/patients/delete/{p["patient_id"]}" class="btn btn-sm btn-danger" onclick="return confirm(\'Delete?\')">Delete</a></td></tr>' for p in patients])}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/patients/add', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        dob = request.form['dob']
        contact = request.form['contact']
        insurance_no = request.form.get('insurance_no', '')
        address = request.form.get('address', '')
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO patients (name, dob, contact, insurance_no, address) VALUES (%s, %s, %s, %s, %s)",
            (name, dob, contact, insurance_no, address)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash('Patient added!', 'success')
        return redirect(url_for('list_patients'))
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Add Patient - MedTrack</title>
    <style>
        body { font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
        input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
    </style>
    </head>
    <body>
        <div class="container">
            <h2>Add New Patient</h2>
            <form method="POST">
                <input type="text" name="name" placeholder="Full Name" required>
                <input type="date" name="dob" placeholder="Date of Birth">
                <input type="text" name="contact" placeholder="Contact Number">
                <input type="text" name="insurance_no" placeholder="Insurance Number">
                <textarea name="address" rows="3" placeholder="Address"></textarea>
                <button type="submit">Save Patient</button>
                <a href="/patients">Cancel</a>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/patients/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        name = request.form['name']
        dob = request.form['dob']
        contact = request.form['contact']
        insurance_no = request.form.get('insurance_no', '')
        address = request.form.get('address', '')
        
        cur.execute(
            "UPDATE patients SET name=%s, dob=%s, contact=%s, insurance_no=%s, address=%s WHERE patient_id=%s",
            (name, dob, contact, insurance_no, address, patient_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash('Patient updated!', 'success')
        return redirect(url_for('list_patients'))
    
    cur.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cur.fetchone()
    cur.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Edit Patient - MedTrack</title>
    <style>
        body {{ font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        input, textarea {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }}
        button {{ background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
    </style>
    </head>
    <body>
        <div class="container">
            <h2>Edit Patient</h2>
            <form method="POST">
                <input type="text" name="name" value="{patient['name']}" required>
                <input type="date" name="dob" value="{patient['dob'] or ''}">
                <input type="text" name="contact" value="{patient['contact'] or ''}">
                <input type="text" name="insurance_no" value="{patient['insurance_no'] or ''}">
                <textarea name="address" rows="3">{patient['address'] or ''}</textarea>
                <button type="submit">Update Patient</button>
                <a href="/patients">Cancel</a>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/patients/delete/<int:patient_id>')
@login_required
def delete_patient(patient_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Patient deleted!', 'success')
    return redirect(url_for('list_patients'))

@app.route('/doctors')
@login_required
def list_doctors():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM doctors ORDER BY name")
    doctors = cur.fetchall()
    cur.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Doctors - MedTrack</title>
    <style>
        body {{ font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
        .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }}
        .btn-danger {{ background: #dc3545; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>👨‍⚕️ Doctor Management</h1>
                <div>
                    <a href="/dashboard" class="btn">Back</a>
                    <a href="/logout" class="btn btn-danger">Logout</a>
                </div>
            </div>
            <div class="card">
                <table>
                    <thead><tr><th>ID</th><th>Name</th><th>Specialization</th><th>Contact</th><th>Email</th></tr></thead>
                    <tbody>
                        {''.join([f'<tr><td>{d["doctor_id"]}</td><td>{d["name"]}</td><td>{d["specialization"] or "N/A"}</td><td>{d["contact"] or "N/A"}</td><td>{d["email"] or "N/A"}</td></tr>' for d in doctors])}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/appointments')
@login_required
def list_appointments():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT a.*, p.name as patient_name, d.name as doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        ORDER BY a.appointment_date DESC
    """)
    appointments = cur.fetchall()
    cur.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Appointments - MedTrack</title>
    <style>
        body {{ font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
        .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }}
        .badge-scheduled {{ background: #17a2b8; color: white; padding: 3px 8px; border-radius: 3px; }}
        .badge-completed {{ background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; }}
        .badge-cancelled {{ background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📅 Appointment Schedule</h1>
                <div>
                    <a href="/dashboard" class="btn">Back</a>
                    <a href="/appointments/add" class="btn">+ Schedule</a>
                    <a href="/logout" class="btn">Logout</a>
                </div>
            </div>
            <div class="card">
                <table>
                    <thead><tr><th>Date</th><th>Patient</th><th>Doctor</th><th>Status</th><th>Reason</th></tr></thead>
                    <tbody>
                        {''.join([f'<tr><td>{a["appointment_date"]}</td><td>{a["patient_name"]}</td><td>{a["doctor_name"]}</td><td><span class="badge-{a["status"]}">{a["status"]}</span></td><td>{a["reason"] or "N/A"}</td></tr>' for a in appointments])}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/appointments/add', methods=['GET', 'POST'])
@login_required
def add_appointment():
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, reason) VALUES (%s, %s, %s, 'scheduled', %s)",
            (request.form['patient_id'], request.form['doctor_id'], request.form['appointment_date'], request.form.get('reason', ''))
        )
        conn.commit()
        cur.close()
        conn.close()
        flash('Appointment scheduled!', 'success')
        return redirect(url_for('list_appointments'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT patient_id, name FROM patients ORDER BY name")
    patients = cur.fetchall()
    cur.execute("SELECT doctor_id, name FROM doctors ORDER BY name")
    doctors = cur.fetchall()
    cur.close()
    conn.close()
    
    patients_options = ''.join([f'<option value="{p["patient_id"]}">{p["name"]}</option>' for p in patients])
    doctors_options = ''.join([f'<option value="{d["doctor_id"]}">{d["name"]}</option>' for d in doctors])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Schedule Appointment - MedTrack</title>
    <style>
        body {{ font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        select, input, textarea {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }}
        button {{ background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
    </style>
    </head>
    <body>
        <div class="container">
            <h2>Schedule New Appointment</h2>
            <form method="POST">
                <select name="patient_id" required><option value="">Select Patient</option>{patients_options}</select>
                <select name="doctor_id" required><option value="">Select Doctor</option>{doctors_options}</select>
                <input type="datetime-local" name="appointment_date" required>
                <textarea name="reason" rows="3" placeholder="Reason for visit"></textarea>
                <button type="submit">Schedule</button>
                <a href="/appointments">Cancel</a>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/visits')
@login_required
def list_visits():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT v.*, p.name as patient_name, d.name as doctor_name
        FROM clinical_visits v
        JOIN patients p ON v.patient_id = p.patient_id
        JOIN doctors d ON v.doctor_id = d.doctor_id
        ORDER BY v.visit_date DESC
    """)
    visits = cur.fetchall()
    cur.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Clinical Visits - MedTrack</title>
    <style>
        body {{ font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
        .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        .btn {{ display: inline-block; padding: 10px 20px; margin: 5px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📋 Clinical Visits</h1>
                <div>
                    <a href="/dashboard" class="btn">Back</a>
                    <a href="/visits/add" class="btn">+ Record Visit</a>
                    <a href="/logout" class="btn">Logout</a>
                </div>
            </div>
            <div class="card">
                <table>
                    <thead><tr><th>Date</th><th>Patient</th><th>Doctor</th><th>Diagnosis</th><th>Treatment</th></tr></thead>
                    <tbody>
                        {''.join([f'<tr><td>{v["visit_date"]}</td><td>{v["patient_name"]}</td><td>{v["doctor_name"]}</td><td>{v["diagnosis"] or "N/A"}</td><td>{v["treatment"] or "N/A"}</td></tr>' for v in visits])}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/visits/add', methods=['GET', 'POST'])
@login_required
def add_visit():
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO clinical_visits (patient_id, doctor_id, visit_date, symptoms, diagnosis, treatment) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (request.form['patient_id'], request.form['doctor_id'], request.form['visit_date'],
              request.form.get('symptoms', ''), request.form.get('diagnosis', ''), request.form.get('treatment', '')))
        conn.commit()
        cur.close()
        conn.close()
        flash('Visit recorded!', 'success')
        return redirect(url_for('list_visits'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT patient_id, name FROM patients ORDER BY name")
    patients = cur.fetchall()
    cur.execute("SELECT doctor_id, name FROM doctors ORDER BY name")
    doctors = cur.fetchall()
    cur.close()
    conn.close()
    
    patients_options = ''.join([f'<option value="{p["patient_id"]}">{p["name"]}</option>' for p in patients])
    doctors_options = ''.join([f'<option value="{d["doctor_id"]}">{d["name"]}</option>' for d in doctors])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Record Visit - MedTrack</title>
    <style>
        body {{ font-family: Arial; margin: 0; padding: 20px; background: #f0f2f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        select, input, textarea {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }}
        button {{ background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
    </style>
    </head>
    <body>
        <div class="container">
            <h2>Record Clinical Visit</h2>
            <form method="POST">
                <select name="patient_id" required><option value="">Select Patient</option>{patients_options}</select>
                <select name="doctor_id" required><option value="">Select Doctor</option>{doctors_options}</select>
                <input type="datetime-local" name="visit_date" required>
                <textarea name="symptoms" rows="3" placeholder="Symptoms"></textarea>
                <textarea name="diagnosis" rows="3" placeholder="Diagnosis"></textarea>
                <textarea name="treatment" rows="3" placeholder="Treatment"></textarea>
                <button type="submit">Save Visit</button>
                <a href="/visits">Cancel</a>
            </form>
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