import MySQLdb
from werkzeug.security import generate_password_hash
from config import Config

def add_sample_data():
    conn = MySQLdb.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        passwd=Config.MYSQL_PASSWORD,
        db=Config.MYSQL_DB
    )
    cursor = conn.cursor()
    
    # Add sample users
    users = [
        ('admin', generate_password_hash('admin123'), 'admin@medtrack.com', 'admin'),
        ('dr_smith', generate_password_hash('doctor123'), 'smith@medtrack.com', 'doctor'),
        ('dr_johnson', generate_password_hash('doctor123'), 'johnson@medtrack.com', 'doctor'),
        ('staff_jane', generate_password_hash('staff123'), 'jane@medtrack.com', 'staff')
    ]
    
    for user in users:
        try:
            cursor.execute(
                "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                user
            )
        except:
            pass
    
    # Add sample patients
    patients = [
        ('John Doe', '1985-03-15', '555-0101', 'INS001', '123 Main St, Toronto'),
        ('Jane Smith', '1990-07-22', '555-0102', 'INS002', '456 Oak Ave, Vancouver'),
        ('Bob Wilson', '1978-11-30', '555-0103', 'INS003', '789 Pine St, Montreal'),
        ('Alice Brown', '1995-01-10', '555-0104', 'INS004', '321 Elm St, Calgary'),
        ('Charlie Davis', '1982-05-18', '555-0105', 'INS005', '654 Maple Dr, Ottawa')
    ]
    
    for patient in patients:
        cursor.execute(
            """INSERT INTO patients (name, dob, contact, insurance_no, address) 
               VALUES (%s, %s, %s, %s, %s)""",
            patient
        )
    
    # Add sample doctors
    doctors = [
        ('Dr. Sarah Smith', 'Cardiology', '555-0201', 'sarah.smith@medtrack.com'),
        ('Dr. Michael Johnson', 'Neurology', '555-0202', 'michael.johnson@medtrack.com'),
        ('Dr. Emily Brown', 'Pediatrics', '555-0203', 'emily.brown@medtrack.com')
    ]
    
    for doctor in doctors:
        cursor.execute(
            """INSERT INTO doctors (name, specialization, contact, email) 
               VALUES (%s, %s, %s, %s)""",
            doctor
        )
    
    # Add sample appointments
    appointments = [
        (1, 1, '2026-04-01 10:00:00', 'scheduled', 'Chest pain'),
        (2, 2, '2026-04-02 14:30:00', 'scheduled', 'Headache'),
        (3, 3, '2026-04-03 11:00:00', 'completed', 'Fever'),
        (4, 1, '2026-04-04 09:30:00', 'scheduled', 'Routine checkup'),
        (5, 2, '2026-04-05 15:00:00', 'cancelled', 'Follow-up')
    ]
    
    for appt in appointments:
        cursor.execute(
            """INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, reason) 
               VALUES (%s, %s, %s, %s, %s)""",
            appt
        )
    
    # Add sample clinical visits
    visits = [
        (1, 1, '2026-03-15 10:30:00', 'Chest pain, shortness of breath', 
         'Angina', 'Prescribed nitroglycerin'),
        (2, 2, '2026-03-16 15:00:00', 'Severe headache, blurred vision', 
         'Migraine', 'Prescribed sumatriptan'),
        (3, 3, '2026-03-17 11:00:00', 'Fever, cough', 
         'Upper respiratory infection', 'Prescribed antibiotics')
    ]
    
    for visit in visits:
        cursor.execute(
            """INSERT INTO clinical_visits (patient_id, doctor_id, visit_date, symptoms, diagnosis, treatment) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            visit
        )
    
    # Add sample prescriptions
    prescriptions = [
        (1, 'Nitroglycerin', '0.4 mg', 'As needed', 'Take under tongue for chest pain'),
        (2, 'Sumatriptan', '50 mg', 'At onset', 'Take at first sign of migraine'),
        (3, 'Amoxicillin', '500 mg', '7 days', 'Take three times daily with food')
    ]
    
    for presc in prescriptions:
        cursor.execute(
            """INSERT INTO prescriptions (visit_id, medicine_name, dosage, duration, instructions) 
               VALUES (%s, %s, %s, %s, %s)""",
            presc
        )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Sample data added successfully!")

if __name__ == '__main__':
    add_sample_data()