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

# Helper function to get doctor_id from user_id
def get_doctor_id_from_user_id(user_id):
    """Get doctor_id from user_id"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT doctor_id FROM doctors WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result['doctor_id'] if result else None

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

# Database Initialization Route
@app.route('/init-db')
def init_database_route():
    """Temporary route to initialize database - REMOVE AFTER USE"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create tables
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) NOT NULL,
                role VARCHAR(20) DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS patients (
                patient_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                dob DATE,
                contact VARCHAR(20),
                insurance_no VARCHAR(50),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                name VARCHAR(100) NOT NULL,
                specialization VARCHAR(100),
                contact VARCHAR(20),
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS staff (
                staff_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                name VARCHAR(100) NOT NULL,
                contact VARCHAR(20),
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id SERIAL PRIMARY KEY,
                patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
                doctor_id INTEGER NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                appointment_date TIMESTAMP NOT NULL,
                status VARCHAR(20) DEFAULT 'scheduled',
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS clinical_visits (
                visit_id SERIAL PRIMARY KEY,
                patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
                doctor_id INTEGER NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                visit_date TIMESTAMP NOT NULL,
                symptoms TEXT,
                diagnosis TEXT,
                treatment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS prescriptions (
                prescription_id SERIAL PRIMARY KEY,
                visit_id INTEGER NOT NULL REFERENCES clinical_visits(visit_id) ON DELETE CASCADE,
                medicine_name VARCHAR(100) NOT NULL,
                dosage VARCHAR(100),
                duration VARCHAR(100),
                instructions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for table in tables:
            cur.execute(table)
        
        conn.commit()
        
        # Add sample admin user
        admin_password = generate_password_hash('admin123')
        cur.execute("""
            INSERT INTO users (username, password, email, role) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ('admin', admin_password, 'admin@medtrack.com', 'admin'))
        
        # Add sample staff user
        staff_password = generate_password_hash('staff123')
        cur.execute("""
            INSERT INTO users (username, password, email, role) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ('staff_jane', staff_password, 'jane@medtrack.com', 'staff'))
        
        # Add sample doctor user
        doctor_password = generate_password_hash('doctor123')
        cur.execute("""
            INSERT INTO users (username, password, email, role) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ('dr_smith', doctor_password, 'smith@medtrack.com', 'doctor'))
        
        conn.commit()
        
        # Add sample patients
        cur.execute("""
            INSERT INTO patients (name, dob, contact, insurance_no, address) 
            VALUES 
                ('John Doe', '1985-03-15', '555-0101', 'INS001', '123 Main St, Toronto'),
                ('Jane Smith', '1990-07-22', '555-0102', 'INS002', '456 Oak Ave, Vancouver'),
                ('Bob Wilson', '1978-11-30', '555-0103', 'INS003', '789 Pine St, Montreal'),
                ('Alice Brown', '1995-01-10', '555-0104', 'INS004', '321 Elm St, Calgary'),
                ('Charlie Davis', '1982-05-18', '555-0105', 'INS005', '654 Maple Dr, Ottawa')
            ON CONFLICT DO NOTHING
        """)
        
        # Add sample doctors
        cur.execute("""
            INSERT INTO doctors (name, specialization, contact, email) 
            VALUES 
                ('Dr. Sarah Smith', 'Cardiology', '555-0201', 'sarah.smith@medtrack.com'),
                ('Dr. Michael Johnson', 'Neurology', '555-0202', 'michael.johnson@medtrack.com'),
                ('Dr. Emily Brown', 'Pediatrics', '555-0203', 'emily.brown@medtrack.com')
            ON CONFLICT DO NOTHING
        """)
        
        conn.commit()
        
        # Add sample appointments
        cur.execute("""
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, reason) 
            VALUES 
                (1, 1, '2026-04-01 10:00:00', 'scheduled', 'Chest pain'),
                (2, 2, '2026-04-02 14:30:00', 'scheduled', 'Headache'),
                (3, 3, '2026-04-03 11:00:00', 'completed', 'Fever'),
                (1, 2, '2026-04-05 09:30:00', 'scheduled', 'Follow-up')
            ON CONFLICT DO NOTHING
        """)
        
        # Add sample clinical visits
        cur.execute("""
            INSERT INTO clinical_visits (patient_id, doctor_id, visit_date, symptoms, diagnosis, treatment) 
            VALUES 
                (1, 1, '2026-03-15 10:30:00', 'Chest pain, shortness of breath', 
                 'Angina', 'Prescribed nitroglycerin'),
                (2, 2, '2026-03-16 15:00:00', 'Severe headache, blurred vision', 
                 'Migraine', 'Prescribed sumatriptan'),
                (3, 3, '2026-03-17 11:00:00', 'Fever, cough', 
                 'Upper respiratory infection', 'Prescribed antibiotics')
            ON CONFLICT DO NOTHING
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
                    max-width: 600px;
                }
                h1 { color: #28a745; }
                .btn {
                    display: inline-block;
                    padding: 10px 20px;
                    margin-top: 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }
                .btn:hover { background: #764ba2; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Database Initialized Successfully!</h1>
                <p>All tables have been created and sample data has been added.</p>
                <h3>Sample Users:</h3>
                <ul>
                    <li><strong>Admin:</strong> admin / admin123</li>
                    <li><strong>Staff:</strong> staff_jane / staff123</li>
                    <li><strong>Doctor:</strong> dr_smith / doctor123</li>
                </ul>
                <a href="/login" class="btn">Go to Login Page</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error - MedTrack</title></head>
        <body>
            <h1>❌ Error Initializing Database</h1>
            <pre>{str(e)}</pre>
            <a href="/">Go to Home</a>
        </body>
        </html>
        """, 500

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

# PATIENT ROUTES
@app.route('/patients')
@login_required
def list_patients():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if session['role'] == 'admin' or session['role'] == 'staff':
        cur.execute("SELECT * FROM patients ORDER BY name")
    else:  # doctor
        cur.execute("""
            SELECT DISTINCT p.* FROM patients p
            LEFT JOIN appointments a ON p.patient_id = a.patient_id AND a.doctor_id = (
                SELECT doctor_id FROM doctors WHERE user_id = %s
            )
            LEFT JOIN clinical_visits v ON p.patient_id = v.patient_id AND v.doctor_id = (
                SELECT doctor_id FROM doctors WHERE user_id = %s
            )
            WHERE a.appointment_id IS NOT NULL OR v.visit_id IS NOT NULL
            ORDER BY p.name
        """, (session['user_id'], session['user_id']))
    
    patients = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('patients/list.html', patients=patients)

@app.route('/patients/add', methods=['GET', 'POST'])
@login_required
@role_required(['staff', 'admin'])
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
@role_required(['staff', 'admin'])
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
@role_required(['staff', 'admin'])
def delete_patient(patient_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Patient deleted successfully!', 'success')
    return redirect(url_for('list_patients'))

@app.route('/patients/view/<int:patient_id>')
@login_required
def view_patient(patient_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if user has access to this patient
    if session['role'] not in ['admin', 'staff']:
        cur.execute("""
            SELECT 1 FROM appointments WHERE patient_id = %s AND doctor_id = (
                SELECT doctor_id FROM doctors WHERE user_id = %s
            )
            UNION
            SELECT 1 FROM clinical_visits WHERE patient_id = %s AND doctor_id = (
                SELECT doctor_id FROM doctors WHERE user_id = %s
            )
        """, (patient_id, session['user_id'], patient_id, session['user_id']))
        if not cur.fetchone():
            flash('You do not have access to this patient', 'danger')
            return redirect(url_for('list_patients'))
    
    # Get patient details
    cur.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cur.fetchone()
    
    # Get all appointments for this patient (full history)
    cur.execute("""
        SELECT a.*, d.name as doctor_name 
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC
    """, (patient_id,))
    appointments = cur.fetchall()
    
    # Get all clinical visits for this patient (full history)
    cur.execute("""
        SELECT v.*, d.name as doctor_name
        FROM clinical_visits v
        JOIN doctors d ON v.doctor_id = d.doctor_id
        WHERE v.patient_id = %s
        ORDER BY v.visit_date DESC
    """, (patient_id,))
    visits = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('patients/view.html', 
                         patient=patient, 
                         appointments=appointments,
                         visits=visits)

# DOCTOR ROUTES
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

@app.route('/doctors/add', methods=['GET', 'POST'])
@login_required
@role_required(['staff', 'admin'])
def add_doctor():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        contact = request.form['contact']
        email = request.form['email']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """INSERT INTO doctors (name, specialization, contact, email) 
               VALUES (%s, %s, %s, %s)""",
            (name, specialization, contact, email)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('list_doctors'))
    
    return render_template('doctors/add.html')

@app.route('/doctors/edit/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@role_required(['staff', 'admin'])
def edit_doctor(doctor_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        contact = request.form['contact']
        email = request.form['email']
        
        cur.execute(
            """UPDATE doctors SET name=%s, specialization=%s, 
               contact=%s, email=%s WHERE doctor_id=%s""",
            (name, specialization, contact, email, doctor_id)
        )
        conn.commit()
        flash('Doctor updated successfully!', 'success')
        cur.close()
        conn.close()
        return redirect(url_for('list_doctors'))
    
    cur.execute("SELECT * FROM doctors WHERE doctor_id = %s", (doctor_id,))
    doctor = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('doctors/edit.html', doctor=doctor)

@app.route('/doctors/delete/<int:doctor_id>')
@login_required
@role_required(['staff', 'admin'])
def delete_doctor(doctor_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Doctor deleted successfully!', 'success')
    return redirect(url_for('list_doctors'))

# APPOINTMENT ROUTES
@app.route('/appointments')
@login_required
def list_appointments():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if session['role'] == 'doctor':
        cur.execute("""
            SELECT a.*, p.name as patient_name, d.name as doctor_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN doctors d ON a.doctor_id = d.doctor_id
            WHERE a.doctor_id = (SELECT doctor_id FROM doctors WHERE user_id = %s)
            ORDER BY a.appointment_date DESC
        """, (session['user_id'],))
    else:
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
    return render_template('appointments/list.html', appointments=appointments)

@app.route('/appointments/add', methods=['GET', 'POST'])
@login_required
def add_appointment():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        
        # If doctor, force their own doctor_id
        if session['role'] == 'doctor':
            cur.execute("SELECT doctor_id FROM doctors WHERE user_id = %s", (session['user_id'],))
            doctor = cur.fetchone()
            if not doctor:
                flash('Doctor profile not found', 'danger')
                return redirect(url_for('dashboard'))
            doctor_id = doctor['doctor_id']
        else:
            doctor_id = request.form['doctor_id']
        
        appointment_date = request.form['appointment_date']
        reason = request.form.get('reason', '')
        
        cur.execute(
            """INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, reason) 
               VALUES (%s, %s, %s, 'scheduled', %s)""",
            (patient_id, doctor_id, appointment_date, reason)
        )
        conn.commit()
        flash('Appointment scheduled successfully!', 'success')
        cur.close()
        conn.close()
        return redirect(url_for('list_appointments'))
    
    # Get patients visible to this user
    if session['role'] in ['admin', 'staff']:
        cur.execute("SELECT patient_id, name FROM patients ORDER BY name")
        patients = cur.fetchall()
        cur.execute("SELECT doctor_id, name, specialization FROM doctors ORDER BY name")
        doctors = cur.fetchall()
    else:  # doctor
        cur.execute("""
            SELECT DISTINCT p.patient_id, p.name FROM patients p
            LEFT JOIN appointments a ON p.patient_id = a.patient_id AND a.doctor_id = (
                SELECT doctor_id FROM doctors WHERE user_id = %s
            )
            LEFT JOIN clinical_visits v ON p.patient_id = v.patient_id AND v.doctor_id = (
                SELECT doctor_id FROM doctors WHERE user_id = %s
            )
            WHERE a.appointment_id IS NOT NULL OR v.visit_id IS NOT NULL
            ORDER BY p.name
        """, (session['user_id'], session['user_id']))
        patients = cur.fetchall()
        doctors = []  # Doctors cannot choose another doctor
    
    cur.close()
    conn.close()
    return render_template('appointments/add.html', patients=patients, doctors=doctors)

@app.route('/appointments/edit/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@role_required(['staff', 'admin'])
def edit_appointment(appointment_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        appointment_date = request.form['appointment_date']
        status = request.form['status']
        reason = request.form.get('reason', '')
        
        cur.execute(
            """UPDATE appointments SET appointment_date=%s, status=%s, reason=%s 
               WHERE appointment_id=%s""",
            (appointment_date, status, reason, appointment_id)
        )
        conn.commit()
        flash('Appointment updated successfully!', 'success')
        cur.close()
        conn.close()
        return redirect(url_for('list_appointments'))
    
    cur.execute("SELECT * FROM appointments WHERE appointment_id = %s", (appointment_id,))
    appointment = cur.fetchone()
    cur.close()
    conn.close()
    
    return render_template('appointments/edit.html', appointment=appointment)

@app.route('/appointments/delete/<int:appointment_id>')
@login_required
@role_required(['staff', 'admin'])
def delete_appointment(appointment_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("DELETE FROM appointments WHERE appointment_id = %s", (appointment_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Appointment cancelled successfully!', 'success')
    return redirect(url_for('list_appointments'))

# CLINICAL VISIT ROUTES
@app.route('/visits')
@login_required
def list_visits():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if session['role'] == 'doctor':
        cur.execute("""
            SELECT v.*, p.name as patient_name, d.name as doctor_name
            FROM clinical_visits v
            JOIN patients p ON v.patient_id = p.patient_id
            JOIN doctors d ON v.doctor_id = d.doctor_id
            WHERE v.doctor_id = (SELECT doctor_id FROM doctors WHERE user_id = %s)
            ORDER BY v.visit_date DESC
        """, (session['user_id'],))
    else:
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
    return render_template('visits/list.html', visits=visits)

@app.route('/visits/add', methods=['GET', 'POST'])
@login_required
def add_visit():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        
        if session['role'] == 'doctor':
            cur.execute("SELECT doctor_id FROM doctors WHERE user_id = %s", (session['user_id'],))
            doctor = cur.fetchone()
            if not doctor:
                flash('Doctor profile not found', 'danger')
                return redirect(url_for('dashboard'))
            doctor_id = doctor['doctor_id']
        else:
            doctor_id = request.form['doctor_id']
        
        visit_date = request.form['visit_date']
        symptoms = request.form.get('symptoms', '')
        diagnosis = request.form.get('diagnosis', '')
        treatment = request.form.get('treatment', '')
        
        cur.execute(
            """INSERT INTO clinical_visits (patient_id, doctor_id, visit_date, symptoms, diagnosis, treatment) 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING visit_id""",
            (patient_id, doctor_id, visit_date, symptoms, diagnosis, treatment)
        )
        visit_id = cur.fetchone()['visit_id']
        conn.commit()
        
        # Add prescriptions if any
        if request.form.get('medicine_name'):
            medicine_name = request.form['medicine_name']
            dosage = request.form.get('dosage', '')
            duration = request.form.get('duration', '')
            instructions = request.form.get('instructions', '')
            
            cur.execute(
                """INSERT INTO prescriptions (visit_id, medicine_name, dosage, duration, instructions) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (visit_id, medicine_name, dosage, duration, instructions)
            )
            conn.commit()
        
        flash('Clinical visit recorded successfully!', 'success')
        cur.close()
        conn.close()
        return redirect(url_for('list_visits'))
    
    # Get visible patients
    if session['role'] in ['admin', 'staff']:
        cur.execute("SELECT patient_id, name FROM patients ORDER BY name")
        patients = cur.fetchall()
        cur.execute("SELECT doctor_id, name, specialization FROM doctors ORDER BY name")
        doctors = cur.fetchall()
    else:
        cur.execute("""
            SELECT DISTINCT p.patient_id, p.name FROM patients p
            LEFT JOIN appointments a ON p.patient_id = a.patient_id AND a.doctor_id = (
                SELECT doctor_id FROM doctors WHERE user_id = %s
            )
            LEFT JOIN clinical_visits v ON p.patient_id = v.patient_id AND v.doctor_id = (
                SELECT doctor_id FROM doctors WHERE user_id = %s
            )
            WHERE a.appointment_id IS NOT NULL OR v.visit_id IS NOT NULL
            ORDER BY p.name
        """, (session['user_id'], session['user_id']))
        patients = cur.fetchall()
        doctors = []
    
    cur.close()
    conn.close()
    return render_template('visits/add.html', patients=patients, doctors=doctors)

@app.route('/visits/view/<int:visit_id>')
@login_required
def view_visit(visit_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get visit details with JOIN
    cur.execute("""
        SELECT v.*, p.name as patient_name, d.name as doctor_name
        FROM clinical_visits v
        JOIN patients p ON v.patient_id = p.patient_id
        JOIN doctors d ON v.doctor_id = d.doctor_id
        WHERE v.visit_id = %s
    """, (visit_id,))
    visit = cur.fetchone()
    
    # Get prescriptions for this visit
    cur.execute("SELECT * FROM prescriptions WHERE visit_id = %s", (visit_id,))
    prescriptions = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('visits/view.html', visit=visit, prescriptions=prescriptions)

# PRESCRIPTION ROUTES
@app.route('/prescriptions/add/<int:visit_id>', methods=['GET', 'POST'])
@login_required
def add_prescription(visit_id):
    if request.method == 'POST':
        medicine_name = request.form['medicine_name']
        dosage = request.form.get('dosage', '')
        duration = request.form.get('duration', '')
        instructions = request.form.get('instructions', '')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """INSERT INTO prescriptions (visit_id, medicine_name, dosage, duration, instructions) 
               VALUES (%s, %s, %s, %s, %s)""",
            (visit_id, medicine_name, dosage, duration, instructions)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Prescription added successfully!', 'success')
        return redirect(url_for('view_visit', visit_id=visit_id))
    
    return render_template('prescriptions/add.html', visit_id=visit_id)

if __name__ == '__main__':
    app.run(debug=True)