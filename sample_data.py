import psycopg2
from werkzeug.security import generate_password_hash
from config import Config

def add_sample_data():
    conn = psycopg2.connect(Config.DATABASE_URL)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM prescriptions CASCADE")
    cursor.execute("DELETE FROM clinical_visits CASCADE")
    cursor.execute("DELETE FROM appointments CASCADE")
    cursor.execute("DELETE FROM staff CASCADE")
    cursor.execute("DELETE FROM doctors CASCADE")
    cursor.execute("DELETE FROM patients CASCADE")
    cursor.execute("DELETE FROM users CASCADE")
    
    # Reset sequences
    cursor.execute("ALTER SEQUENCE users_user_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE patients_patient_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE doctors_doctor_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE appointments_appointment_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE clinical_visits_visit_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE prescriptions_prescription_id_seq RESTART WITH 1")
    
    # Add sample users
    users = [
        ('admin', generate_password_hash('admin123'), 'admin@medtrack.com', 'admin'),
        ('staff_jane', generate_password_hash('staff123'), 'jane@medtrack.com', 'staff'),
        ('dr_smith', generate_password_hash('doctor123'), 'sarah.smith@medtrack.com', 'doctor'),
        ('dr_johnson', generate_password_hash('doctor123'), 'michael.johnson@medtrack.com', 'doctor'),
        ('dr_brown', generate_password_hash('doctor123'), 'emily.brown@medtrack.com', 'doctor'),
        ('dr_wilson', generate_password_hash('doctor123'), 'james.wilson@medtrack.com', 'doctor'),
        ('dr_anderson', generate_password_hash('doctor123'), 'lisa.anderson@medtrack.com', 'doctor')
    ]
    
    print("Adding users...")
    for user in users:
        try:
            cursor.execute(
                "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                user
            )
            print(f"  ✓ Added user: {user[0]}")
        except Exception as e:
            print(f"  ✗ Error adding {user[0]}: {e}")
    
    # Get user IDs for doctors
    cursor.execute("SELECT user_id, username FROM users WHERE role = 'doctor'")
    doctor_users = {row[1]: row[0] for row in cursor.fetchall()}
    
    # Add sample patients
    patients = [
        ('John Doe', '1985-03-15', '555-0101', 'INS001', '123 Main St, Toronto'),
        ('Jane Smith', '1990-07-22', '555-0102', 'INS002', '456 Oak Ave, Vancouver'),
        ('Bob Wilson', '1978-11-30', '555-0103', 'INS003', '789 Pine St, Montreal'),
        ('Alice Brown', '1995-01-10', '555-0104', 'INS004', '321 Elm St, Calgary'),
        ('Charlie Davis', '1982-05-18', '555-0105', 'INS005', '654 Maple Dr, Ottawa'),
        ('Emma Wilson', '1988-09-25', '555-0106', 'INS006', '789 Queen St, Toronto'),
        ('Michael Lee', '1992-12-03', '555-0107', 'INS007', '321 King St, Vancouver')
    ]
    
    print("\nAdding patients...")
    for patient in patients:
        cursor.execute(
            """INSERT INTO patients (name, dob, contact, insurance_no, address) 
               VALUES (%s, %s, %s, %s, %s) RETURNING patient_id""",
            patient
        )
        patient_id = cursor.fetchone()[0]
        print(f"  ✓ Added patient: {patient[0]} (ID: {patient_id})")
    
    # Add sample doctors with user_id links
    doctors = [
        ('dr_smith', 'Dr. Sarah Smith', 'Cardiology', '555-0201', 'sarah.smith@medtrack.com'),
        ('dr_johnson', 'Dr. Michael Johnson', 'Neurology', '555-0202', 'michael.johnson@medtrack.com'),
        ('dr_brown', 'Dr. Emily Brown', 'Pediatrics', '555-0203', 'emily.brown@medtrack.com'),
        ('dr_wilson', 'Dr. James Wilson', 'Cardiology', '555-0204', 'james.wilson@medtrack.com'),
        ('dr_anderson', 'Dr. Lisa Anderson', 'Dermatology', '555-0205', 'lisa.anderson@medtrack.com')
    ]
    
    print("\nAdding doctors...")
    for username, name, specialization, contact, email in doctors:
        user_id = doctor_users.get(username)
        cursor.execute(
            """INSERT INTO doctors (user_id, name, specialization, contact, email) 
               VALUES (%s, %s, %s, %s, %s) RETURNING doctor_id""",
            (user_id, name, specialization, contact, email)
        )
        doctor_id = cursor.fetchone()[0]
        print(f"  ✓ Added doctor: {name} (ID: {doctor_id})")
    
    # Add sample appointments with multiple doctors per patient (joint patients)
    # Patient 1 (John Doe) sees multiple doctors
    appointments = [
        # Dr. Smith's patients
        (1, 1, '2026-04-01 10:00:00', 'scheduled', 'Chest pain - initial consult'),
        (4, 1, '2026-04-03 14:30:00', 'scheduled', 'Routine heart checkup'),
        (6, 1, '2026-04-05 11:00:00', 'completed', 'High blood pressure follow-up'),
        
        # Dr. Johnson's patients
        (2, 2, '2026-04-02 09:30:00', 'scheduled', 'Severe migraines'),
        (5, 2, '2026-04-04 15:00:00', 'scheduled', 'Memory loss concerns'),
        (7, 2, '2026-04-06 13:00:00', 'completed', 'Stroke follow-up'),
        
        # Dr. Brown's patients
        (3, 3, '2026-04-01 13:30:00', 'scheduled', 'Child fever and cough'),
        (1, 3, '2026-04-07 14:00:00', 'scheduled', 'Child vaccination'),  # Joint patient
        (4, 3, '2026-04-08 10:00:00', 'scheduled', 'Pediatric checkup'),
        
        # Dr. Wilson's patients (Cardiology)
        (1, 4, '2026-04-09 11:00:00', 'scheduled', 'Second opinion on heart condition'),  # Joint patient
        (4, 4, '2026-04-10 14:00:00', 'scheduled', 'ECG results review'),
        (6, 4, '2026-04-11 09:00:00', 'scheduled', 'Stress test results'),
        
        # Dr. Anderson's patients (Dermatology)
        (2, 5, '2026-04-12 13:00:00', 'scheduled', 'Skin rash evaluation'),
        (5, 5, '2026-04-13 15:30:00', 'scheduled', 'Acne treatment'),
        (3, 5, '2026-04-14 10:30:00', 'scheduled', 'Eczema follow-up')
    ]
    
    print("\nAdding appointments...")
    for appt in appointments:
        cursor.execute(
            """INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, reason) 
               VALUES (%s, %s, %s, %s, %s)""",
            appt
        )
        print(f"  ✓ Added appointment: Patient {appt[0]} with Doctor {appt[1]}")
    
    # Add sample clinical visits
    visits = [
        # Dr. Smith's visits
        (1, 1, '2026-03-15 10:30:00', 'Chest pain, shortness of breath, fatigue', 
         'Angina pectoris', 'Prescribed nitroglycerin and ordered stress test'),
        (4, 1, '2026-03-20 14:00:00', 'Irregular heartbeat, dizziness', 
         'Atrial fibrillation', 'Prescribed blood thinners'),
        (6, 1, '2026-03-25 11:30:00', 'High BP reading, headache', 
         'Hypertension Stage 2', 'Prescribed Lisinopril'),
        
        # Dr. Johnson's visits
        (2, 2, '2026-03-16 09:00:00', 'Severe headache with aura, nausea', 
         'Migraine with aura', 'Prescribed Sumatriptan'),
        (5, 2, '2026-03-18 15:30:00', 'Memory gaps, confusion', 
         'Early stage dementia', 'Referred to neurologist'),
        (7, 2, '2026-03-22 10:00:00', 'Weakness on right side', 
         'Ischemic stroke recovery', 'Physical therapy scheduled'),
        
        # Dr. Brown's visits
        (3, 3, '2026-03-17 11:00:00', 'High fever, sore throat, cough', 
         'Strep throat', 'Prescribed Amoxicillin'),
        (1, 3, '2026-03-24 15:00:00', 'Ear pain, fever', 
         'Ear infection', 'Prescribed antibiotics and ear drops'),
        
        # Dr. Wilson's visits (Cardiology)
        (1, 4, '2026-03-19 09:30:00', 'Chest discomfort during exercise', 
         'Stable angina', 'Prescribed nitroglycerin and beta-blockers'),
        (4, 4, '2026-03-21 13:00:00', 'Abnormal ECG results', 
         'Sinus arrhythmia', 'Monitoring and lifestyle changes'),
        
        # Dr. Anderson's visits (Dermatology)
        (2, 5, '2026-03-23 14:30:00', 'Itchy red rash on arms', 
         'Contact dermatitis', 'Prescribed hydrocortisone cream'),
        (5, 5, '2026-03-26 11:00:00', 'Cystic acne on face', 
         'Acne vulgaris', 'Prescribed topical retinoid')
    ]
    
    print("\nAdding clinical visits...")
    for visit in visits:
        cursor.execute(
            """INSERT INTO clinical_visits (patient_id, doctor_id, visit_date, symptoms, diagnosis, treatment) 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING visit_id""",
            visit
        )
        visit_id = cursor.fetchone()[0]
        print(f"  ✓ Added visit ID {visit_id}")
    
    # Add sample prescriptions
    prescriptions = [
        (1, 'Nitroglycerin', '0.4 mg', 'As needed', 'Take sublingually for chest pain'),
        (1, 'Aspirin', '81 mg', 'Daily', 'Take once daily with food'),
        (2, 'Warfarin', '5 mg', 'Ongoing', 'Take daily, monitor INR'),
        (3, 'Lisinopril', '10 mg', 'Ongoing', 'Take once daily'),
        (4, 'Sumatriptan', '50 mg', 'At onset', 'Take at first sign of migraine'),
        (5, 'Donepezil', '5 mg', 'Ongoing', 'Take at bedtime'),
        (6, 'Amoxicillin', '500 mg', '10 days', 'Take twice daily'),
        (7, 'Amoxicillin', '250 mg', '7 days', 'Take twice daily'),
        (8, 'Nitroglycerin', '0.4 mg', 'As needed', 'Take before exercise'),
        (9, 'Metoprolol', '25 mg', 'Daily', 'Take once daily'),
        (10, 'Hydrocortisone', '1% cream', '14 days', 'Apply twice daily'),
        (11, 'Tretinoin', '0.025% cream', 'Ongoing', 'Apply at night')
    ]
    
    print("\nAdding prescriptions...")
    for presc in prescriptions:
        cursor.execute(
            """INSERT INTO prescriptions (visit_id, medicine_name, dosage, duration, instructions) 
               VALUES (%s, %s, %s, %s, %s)""",
            presc
        )
        print(f"  ✓ Added prescription for visit {presc[0]}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n" + "="*50)
    print("✅ SAMPLE DATA ADDED SUCCESSFULLY!")
    print("="*50)
    print("\n📊 DATA SUMMARY:")
    print(f"  • Users: {len(users)}")
    print(f"  • Patients: {len(patients)}")
    print(f"  • Doctors: {len(doctors)}")
    print(f"  • Appointments: {len(appointments)}")
    print(f"  • Clinical Visits: {len(visits)}")
    print(f"  • Prescriptions: {len(prescriptions)}")
    
    print("\n🔐 LOGIN CREDENTIALS:")
    print("  Admin:   admin / admin123")
    print("  Staff:   staff_jane / staff123")
    print("  Doctors: (all use password: doctor123)")
    for username, _, _, _ in users:
        if username.startswith('dr_'):
            print(f"    • {username}")
    
    print("\n👥 ROLE-BASED ACCESS:")
    print("  • Admin & Staff: Can see ALL doctors and ALL patients")
    print("  • Doctors: Can ONLY see their own patients")
    print("  • Joint Patients: If a patient sees multiple doctors,")
    print("    each doctor can see the patient's complete history")
    print("\n📋 JOINT PATIENTS EXAMPLE:")
    print("  • John Doe (Patient 1) sees: Dr. Smith, Dr. Brown, Dr. Wilson")
    print("  • Each of these doctors can see John Doe's full history")

if __name__ == '__main__':
    add_sample_data()
