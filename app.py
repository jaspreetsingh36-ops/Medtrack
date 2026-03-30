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
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/init-db')
def init_database_route():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Drop existing tables in correct order
        cur.execute("DROP TABLE IF EXISTS prescriptions CASCADE")
        cur.execute("DROP TABLE IF EXISTS clinical_visits CASCADE")
        cur.execute("DROP TABLE IF EXISTS appointments CASCADE")
        cur.execute("DROP TABLE IF EXISTS staff CASCADE")
        cur.execute("DROP TABLE IF EXISTS doctors CASCADE")
        cur.execute("DROP TABLE IF EXISTS patients CASCADE")
        cur.execute("DROP TABLE IF EXISTS users CASCADE")
        
        # Create tables
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
            CREATE TABLE staff (
                staff_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                name VARCHAR(100) NOT NULL,
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
        
        # Create users with proper password hashes
        admin_hash = generate_password_hash('admin123')
        staff_hash = generate_password_hash('staff123')
        doctor_hash = generate_password_hash('doctor123')
        
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('admin', admin_hash, 'admin@medtrack.com', 'admin'))
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('staff_jane', staff_hash, 'jane@medtrack.com', 'staff'))
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('dr_smith', doctor_hash, 'smith@medtrack.com', 'doctor'))
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('dr_johnson', doctor_hash, 'michael.johnson@medtrack.com', 'doctor'))
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                    ('dr_brown', doctor_hash, 'emily.brown@medtrack.com', 'doctor'))
        conn.commit()
        
        # Get user IDs and create doctor profiles
        cur.execute("SELECT user_id FROM users WHERE username = 'dr_smith'")
        dr_smith_id = cur.fetchone()[0]
        cur.execute("INSERT INTO doctors (user_id, name, specialization, contact, email) VALUES (%s, %s, %s, %s, %s)",
                    (dr_smith_id, 'Dr. Sarah Smith', 'Cardiology', '555-0201', 'sarah.smith@medtrack.com'))
        
        cur.execute("SELECT user_id FROM users WHERE username = 'dr_johnson'")
        dr_johnson_id = cur.fetchone()[0]
        cur.execute("INSERT INTO doctors (user_id, name, specialization, contact, email) VALUES (%s, %s, %s, %s, %s)",
                    (dr_johnson_id, 'Dr. Michael Johnson', 'Neurology', '555-0202', 'michael.johnson@medtrack.com'))
        
        cur.execute("SELECT user_id FROM users WHERE username = 'dr_brown'")
        dr_brown_id = cur.fetchone()[0]
        cur.execute("INSERT INTO doctors (user_id, name, specialization, contact, email) VALUES (%s, %s, %s, %s, %s)",
                    (dr_brown_id, 'Dr. Emily Brown', 'Pediatrics', '555-0203', 'emily.brown@medtrack.com'))
        conn.commit()
        
        # Add patients
        cur.execute("""
            INSERT INTO patients (name, dob, contact, insurance_no, address) VALUES 
            ('John Doe', '1985-03-15', '555-0101', 'INS001', '123 Main St, Toronto'),
            ('Jane Smith', '1990-07-22', '555-0102', 'INS002', '456 Oak Ave, Vancouver'),
            ('Bob Wilson', '1978-11-30', '555-0103', 'INS003', '789 Pine St, Montreal'),
            ('Alice Brown', '1995-01-10', '555-0104', 'INS004', '321 Elm St, Calgary'),
            ('Charlie Davis', '1982-05-18', '555-0105', 'INS005', '654 Maple Dr, Ottawa')
        """)
        conn.commit()
        
        # Add appointments
        cur.execute("""
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, reason) VALUES 
            (1, 1, '2026-04-01 10:00:00', 'scheduled', 'Chest pain'),
            (2, 2, '2026-04-02 14:30:00', 'scheduled', 'Headache'),
            (3, 3, '2026-04-03 11:00:00', 'completed', 'Fever')
        """)
        conn.commit()
        
        cur.close()
        conn.close()
        
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Database Initialized - MedTrack</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
                .container { background: white; border-radius: 10px; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); max-width: 600px; }
                h1 { color: #28a745; }
                .btn { display: inline-block; padding: 10px 20px; margin-top: 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }
                .btn:hover { background: #764ba2; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Database Initialized Successfully!</h1>
                <p>All tables created with fresh data.</p>
                <h3>Login Credentials:</h3>
                <ul>
                    <li><strong>Admin:</strong> admin / admin123</li>
                    <li><strong>Staff:</strong> staff_jane / staff123</li>
                    <li><strong>Doctors:</strong> dr_smith / doctor123, dr_johnson / doctor123, dr_brown / doctor123</li>
                </ul>
                <a href="/login" class="btn">Go to Login Page</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f'<h1>Error: {str(e)}</h1>'

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user:
            flash('Username already exists', 'danger')
            cur.close()
            conn.close()
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s) RETURNING user_id",
            (username, hashed_password, email, role)
        )
        user_id = cur.fetchone()['user_id']
        conn.commit()
        
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
            session.clear()
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            session.permanent = True
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
    
    cur.execute("SELECT COUNT(*) as count FROM patients")
    patient_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM doctors")
    doctor_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM appointments WHERE status = 'scheduled'")
    appointment_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM clinical_visits WHERE visit_date >= CURRENT_DATE")
    visit_count = cur.fetchone()['count']
    
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
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """INSERT INTO patients (name, dob, contact, insurance_no, address) 
               VALUES (%s, %s, %s, %s, %s)""",
            (name, dob, contact, insurance_no, address)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Patient added successfully!', 'success')
        return redirect(url_for('list_patients'))
    
    return render_template('patients/add.html')

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
            """UPDATE patients SET name=%s, dob=%s, contact=%s, 
               insurance_no=%s, address=%s WHERE patient_id=%s""",
            (name, dob, contact, insurance_no, address, patient_id)
        )
        conn.commit()
        flash('Patient updated successfully!', 'success')
        cur.close()
        conn.close()
        return redirect(url_for('list_patients'))
    
    cur.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('patients/edit.html', patient=patient)

@app.route('/patients/delete/<int:patient_id>')
@login_required
def delete_patient(patient_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Patient deleted successfully!', 'success')
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
    return render_template('doctors/list.html', doctors=doctors)

if __name__ == '__main__':
    app.run(debug=True)