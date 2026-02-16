"""
Database Seed Script

This script populates the database with sample data for testing and development.
It is idempotent - can be run multiple times safely.

Usage:
    python scripts/seed_database.py

Requirements: 2.5
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, time, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import after adding to path
try:
    import asyncpg
except ImportError:
    print("Error: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_database")


# Sample data
SPECIALTIES = [
    "General Medicine",
    "Cardiology",
    "Dermatology",
    "Neurology",
    "Pediatrics",
    "Orthopedics",
    "Psychiatry",
    "Ophthalmology",
]

SYMPTOMS = [
    ("Fever", "General Medicine"),
    ("Cough", "General Medicine"),
    ("Chest Pain", "Cardiology"),
    ("Heart Palpitations", "Cardiology"),
    ("Skin Rash", "Dermatology"),
    ("Acne", "Dermatology"),
    ("Headache", "Neurology"),
    ("Migraine", "Neurology"),
    ("Child Fever", "Pediatrics"),
    ("Vaccination", "Pediatrics"),
    ("Joint Pain", "Orthopedics"),
    ("Back Pain", "Orthopedics"),
    ("Anxiety", "Psychiatry"),
    ("Depression", "Psychiatry"),
    ("Eye Pain", "Ophthalmology"),
    ("Blurred Vision", "Ophthalmology"),
]

DOCTORS = [
    ("Dr. Sarah Johnson", "General Medicine", 15, "MD"),
    ("Dr. Michael Chen", "Cardiology", 20, "MD, FACC"),
    ("Dr. Emily Rodriguez", "Dermatology", 12, "MD, FAAD"),
    ("Dr. David Kim", "Neurology", 18, "MD, PhD"),
    ("Dr. Lisa Anderson", "Pediatrics", 10, "MD, FAAP"),
    ("Dr. James Wilson", "Orthopedics", 22, "MD, FAAOS"),
    ("Dr. Maria Garcia", "Psychiatry", 14, "MD, Psychiatrist"),
    ("Dr. Robert Taylor", "Ophthalmology", 16, "MD, FACS"),
    ("Dr. Jennifer Lee", "General Medicine", 8, "MD"),
    ("Dr. William Brown", "Cardiology", 25, "MD, FACC"),
]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


async def seed_database():
    """Main function to seed the database."""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    logger.info("Connecting to database...")
    
    try:
        conn = await asyncpg.connect(database_url)
        logger.info("Connected successfully")
        
        # Check if data already exists
        existing_doctors = await conn.fetchval("SELECT COUNT(*) FROM doctor")
        if existing_doctors > 0:
            logger.info(f"Database already has {existing_doctors} doctors. Skipping seed (idempotent).")
            await conn.close()
            return True
        
        logger.info("Starting database seeding...")
        
        # 1. Seed Specialties
        logger.info("Seeding specialties...")
        specialty_ids = {}
        for spec_name in SPECIALTIES:
            spec_id = await conn.fetchval(
                "INSERT INTO specialty (spec_name) VALUES ($1) RETURNING spec_id",
                spec_name
            )
            specialty_ids[spec_name] = spec_id
            logger.info(f"  Added specialty: {spec_name}")
        
        # 2. Seed Symptoms and link to specialties
        logger.info("Seeding symptoms...")
        for sym_name, spec_name in SYMPTOMS:
            # Insert symptom
            sym_id = await conn.fetchval(
                "INSERT INTO symptoms (sym_name) VALUES ($1) ON CONFLICT (sym_name) DO UPDATE SET sym_name = $1 RETURNING sym_id",
                sym_name
            )
            
            # Link to specialty
            spec_id = specialty_ids[spec_name]
            await conn.execute(
                "INSERT INTO spec_sym (spec_id, sym_id, confidence) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                spec_id, sym_id, 0.9
            )
            logger.info(f"  Added symptom: {sym_name} → {spec_name}")
        
        # 3. Seed Doctors
        logger.info("Seeding doctors...")
        doctor_ids = []
        for doc_name, spec_name, experience, degree in DOCTORS:
            # Insert doctor
            doc_id = await conn.fetchval(
                """INSERT INTO doctor (name, experiences, degree_doc, status, is_active)
                   VALUES ($1, $2, $3, 'Active', true) RETURNING doc_id""",
                doc_name, experience, degree
            )
            doctor_ids.append((doc_id, doc_name))
            
            # Link to specialty
            spec_id = specialty_ids[spec_name]
            await conn.execute(
                "INSERT INTO doctor_specialty (doc_id, spec_id) VALUES ($1, $2)",
                doc_id, spec_id
            )
            
            logger.info(f"  Added doctor: {doc_name} ({spec_name})")
        
        # 4. Seed Doctor Shifts (9 AM - 5 PM, Monday-Friday)
        logger.info("Seeding doctor shifts...")
        for doc_id, doc_name in doctor_ids:
            for weekday in WEEKDAYS:
                await conn.execute(
                    """INSERT INTO doc_shift (doc_id, day_of_week, start_time, end_time, status)
                       VALUES ($1, $2::weekday_enum, $3, $4, 'Active')""",
                    doc_id, weekday, time(9, 0), time(17, 0)
                )
            logger.info(f"  Added shifts for: {doc_name}")
        
        # 5. Seed Sample Patient Accounts
        logger.info("Seeding sample patient accounts...")
        sample_accounts = [
            "+1234567890",
            "+1234567891",
            "+1234567892",
        ]
        
        for mobile in sample_accounts:
            await conn.execute(
                "INSERT INTO patient_account (mobile_no) VALUES ($1) ON CONFLICT DO NOTHING",
                mobile
            )
            logger.info(f"  Added patient account: {mobile}")
        
        # 6. Seed Sample Patients
        logger.info("Seeding sample patients...")
        account_id_1 = await conn.fetchval(
            "SELECT account_id FROM patient_account WHERE mobile_no = $1",
            "+1234567890"
        )
        
        if account_id_1:
            await conn.execute(
                """INSERT INTO patient (account_id, name, gender, dob)
                   VALUES ($1, $2, $3::gender_enum, $4)""",
                account_id_1, "John Doe", "Male", datetime(1985, 5, 15).date()
            )
            logger.info("  Added patient: John Doe")
        
        # 7. Seed Sample Appointments (future dates)
        logger.info("Seeding sample appointments...")
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_10am = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        
        pt_id = await conn.fetchval(
            "SELECT pt_id FROM patient WHERE name = $1",
            "John Doe"
        )
        
        if pt_id and doctor_ids:
            doc_id = doctor_ids[0][0]  # First doctor
            await conn.execute(
                """INSERT INTO appointment (account_id, pt_id, doc_id, reason, date_time, app_status)
                   VALUES ($1, $2, $3, $4, $5, 'Booked')""",
                account_id_1, pt_id, doc_id, "Annual checkup", tomorrow_10am
            )
            logger.info(f"  Added appointment: John Doe with {doctor_ids[0][1]}")
        
        await conn.close()
        logger.info("✅ Database seeding completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(seed_database())
    sys.exit(0 if success else 1)
