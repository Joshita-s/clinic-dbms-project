import mysql.connector
import pandas as pd
import streamlit as st
from datetime import datetime

# ==========================================
# DATABASE CONFIGURATION
# ==========================================
DB_HOST = "localhost"
DB_USER = "root"  # MySQL root user
DB_PASSWORD = "123456789"  # Replace with your actual MySQL password
DB_NAME = "clinic_db"


def connect_db():
    """Connects to MySQL server and returns the database connection."""
    try:
        # Step 1: Ensure database exists on MySQL server
        base_conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD
        )
        cursor = base_conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};")
        cursor.close()
        base_conn.close()

        # Step 2: Connect to the clinic database
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Couldn't connect to MySQL: {err}")
        return None


def setup_tables():
    """Creates database tables for patients, doctors, and appointments."""
    conn = connect_db()
    if conn:
        cursor = conn.cursor()

        # Patients Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                age INT,
                gender VARCHAR(20),
                phone VARCHAR(15) UNIQUE NOT NULL,
                blood_group VARCHAR(10),
                notes TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Doctors Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS doctors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                specialty VARCHAR(100) NOT NULL,
                phone VARCHAR(15)
            );
        """
        )

        # Appointments Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT,
                doctor_id INT,
                visit_date DATE,
                slot_time VARCHAR(20),
                reason TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
            );
        """
        )

        conn.commit()
        cursor.close()
        conn.close()


# Run table setup on initial load
setup_tables()

# ==========================================
# CLINIC APPLICATION UI
# ==========================================
st.set_page_config(page_title="Clinic Workspace", page_icon="🩺", layout="wide")

st.sidebar.markdown("## 🩺 Care Desk")
st.sidebar.caption("Welcome back! Select a workspace tab below.")

tab = st.sidebar.radio(
    "Go to",
    [
        "Overview",
        "New Patient Check-in",
        "Patient Records",
        "Schedule Visit",
        "Today's Visits",
        "Doctors Team",
    ],
)

conn = connect_db()

# --- 1. OVERVIEW ---
if tab == "Overview":
    st.title("👋 Good day!")
    st.write("Here is a quick snapshot of what's happening at the clinic today.")

    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patients")
        p_total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM doctors")
        d_total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM appointments WHERE visit_date = CURDATE()"
        )
        v_today = cursor.fetchone()[0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Registered Patients", p_total)
        c2.metric("Scheduled Visits Today", v_today)
        c3.metric("Available Doctors", d_total)
        cursor.close()

# --- 2. NEW PATIENT CHECK-IN ---
elif tab == "New Patient Check-in":
    st.title("📝 New Patient Intake")
    st.write("Enter patient information to create a new profile.")

    with st.form("intake_form", clear_on_submit=True):
        full_name = st.text_input("Full Name *")

        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Age", min_value=0, max_value=120, value=30)
        gender = c2.selectbox("Gender", ["Female", "Male", "Non-binary / Other"])
        blood_group = c3.selectbox(
            "Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
        )

        phone = st.text_input("Phone Number *")
        notes = st.text_area("Medical History / Allergies / Notes")

        submitted = st.form_submit_button("Register Patient Profile")

        if submitted:
            if not full_name or not phone:
                st.warning("Please fill out the patient's name and phone number.")
            else:
                try:
                    cursor = conn.cursor()
                    q = "INSERT INTO patients (full_name, age, gender, phone, blood_group, notes) VALUES (%s, %s, %s, %s, %s, %s)"
                    cursor.execute(
                        q, (full_name, age, gender, phone, blood_group, notes)
                    )
                    conn.commit()
                    st.success(
                        f"Successfully saved **{full_name}** to the clinic database!"
                    )
                    cursor.close()
                except mysql.connector.Error as e:
                    st.error(f"Couldn't save record: {e}")

# --- 3. PATIENT RECORDS ---
elif tab == "Patient Records":
    st.title("📂 Patient Directory")
    if conn:
        df = pd.read_sql(
            "SELECT id, full_name, age, gender, phone, blood_group, notes, joined_date FROM patients ORDER BY id DESC",
            conn,
        )

        search = st.text_input(
            "🔍 Search by name or phone number", placeholder="Type to filter..."
        )
        if search:
            df = df[
                df["full_name"].str.contains(search, case=False, na=False)
                | df["phone"].str.contains(search, case=False, na=False)
            ]

        st.dataframe(df, use_container_width=True)

# --- 4. SCHEDULE VISIT ---
elif tab == "Schedule Visit":
    st.title("📅 Book a Patient Visit")

    patients_df = pd.read_sql("SELECT id, full_name, phone FROM patients", conn)
    doctors_df = pd.read_sql("SELECT id, full_name, specialty FROM doctors", conn)

    if patients_df.empty or doctors_df.empty:
        st.info(
            "💡 Please make sure you have at least one patient and one doctor registered before scheduling a visit."
        )
    else:
        p_map = {
            f"{row['full_name']} ({row['phone']})": row["id"]
            for _, row in patients_df.iterrows()
        }
        d_map = {
            f"Dr. {row['full_name']} ({row['specialty']})": row["id"]
            for _, row in doctors_df.iterrows()
        }

        patient_choice = st.selectbox("Select Patient", list(p_map.keys()))
        doctor_choice = st.selectbox("Select Doctor", list(d_map.keys()))

        c1, c2 = st.columns(2)
        visit_date = c1.date_input("Date of Visit", min_value=datetime.today())
        slot_time = c2.selectbox(
            "Time Slot",
            [
                "09:00 AM",
                "10:00 AM",
                "11:30 AM",
                "02:00 PM",
                "03:30 PM",
                "05:00 PM",
            ],
        )

        reason = st.text_area("Chief Complaint / Symptoms")

        if st.button("Confirm Appointment"):
            cursor = conn.cursor()
            p_id = p_map[patient_choice]
            d_id = d_map[doctor_choice]

            q = "INSERT INTO appointments (patient_id, doctor_id, visit_date, slot_time, reason) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(q, (p_id, d_id, visit_date, slot_time, reason))
            conn.commit()
            st.success("Appointment booked successfully!")
            cursor.close()

# --- 5. TODAY'S VISITS ---
elif tab == "Today's Visits":
    st.title("📋 Today's Appointments")

    q = """
    SELECT a.id, p.full_name AS Patient, p.phone AS Contact, d.full_name AS Doctor, a.slot_time AS Time, a.reason AS Notes
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    JOIN doctors d ON a.doctor_id = d.id
    WHERE a.visit_date = CURDATE()
    ORDER BY a.slot_time;
    """
    df_today = pd.read_sql(q, conn)
    if df_today.empty:
        st.write("No visits scheduled for today.")
    else:
        st.dataframe(df_today, use_container_width=True)

# --- 6. DOCTORS TEAM ---
elif tab == "Doctors Team":
    st.title("👨‍⚕ Clinic Doctors")

    with st.expander("➕ Add New Doctor"):
        with st.form("add_doctor"):
            doc_name = st.text_input("Doctor's Name")
            specialty = st.text_input("Specialty / Department")
            doc_phone = st.text_input("Contact Phone")

            if st.form_submit_button("Save Doctor Profile"):
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO doctors (full_name, specialty, phone) VALUES (%s, %s, %s)",
                    (doc_name, specialty, doc_phone),
                )
                conn.commit()
                st.success(f"Dr. {doc_name} added to the team!")
                cursor.close()

    df_docs = pd.read_sql(
        "SELECT id, full_name, specialty, phone FROM doctors", conn
    )
    st.dataframe(df_docs, use_container_width=True)

if conn:
    conn.close()
