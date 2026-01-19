import logging
import json
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any, Tuple
from memory.service import get_memory_service

logger = logging.getLogger("hospital-service")

class HospitalService:
    """
    Service for interacting with the hospital-specific tables in the database.
    (Doctors, Appointments, Patients, Specialties, etc.)
    
    Reuses the connection pool from the main MemoryService.
    """
    
    def __init__(self):
        self.memory_service = get_memory_service()
        
    async def _fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Helper to fetch rows using the shared pool."""
        if not self.memory_service._pool:
            if self.memory_service.is_enabled:
                await self.memory_service.initialize()
            if not self.memory_service._pool:
                logger.error("Database pool not available")
                return []
                
        try:
            async with self.memory_service._pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"DB Fetch Error: {e} | Query: {query}")
            return []

    async def _fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Helper to fetch a single row."""
        if not self.memory_service._pool:
            if self.memory_service.is_enabled:
                await self.memory_service.initialize()
            if not self.memory_service._pool:
                return None
                
        try:
            async with self.memory_service._pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"DB FetchRow Error: {e} | Query: {query}")
            return None

    async def _execute(self, query: str, *args) -> str:
        """Helper to execute a command (INSERT, UPDATE, DELETE)."""
        if not self.memory_service._pool:
            if self.memory_service.is_enabled:
                await self.memory_service.initialize()
            if not self.memory_service._pool:
                return "DB Unavailable"
                
        try:
            async with self.memory_service._pool.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"DB Execute Error: {e} | Query: {query}")
            return f"Error: {str(e)}"

    # --- Specialty & Doctor Search ---

    async def search_specialty_by_symptom(self, symptom_tokens: List[str]) -> List[Tuple[str, str]]:
        """
        Finds specialties matching the given symptom tokens.
        Returns list of (token, specialty_name).
        """
        query = """
            SELECT DISTINCT s.spec_name 
            FROM specialty s
            JOIN spec_sym ss ON s.spec_id = ss.spec_id
            JOIN symptoms sy ON ss.sym_id = sy.sym_id
            WHERE LOWER(sy.sym_name) LIKE $1
            LIMIT 1;
        """
        matches = []
        for token in symptom_tokens:
            row = await self._fetchrow(query, f"%{token}%")
            if row:
                matches.append((token, row["spec_name"]))
        return matches

    async def get_doctors_by_specialty(self, specialty: str) -> List[str]:
        """Returns list of active doctor names for a specialty."""
        query = """
            SELECT d.name 
            FROM doctor d
            JOIN doctor_specialty ds ON d.doc_id = ds.doc_id
            JOIN specialty s ON ds.spec_id = s.spec_id
            WHERE LOWER(s.spec_name) LIKE $1 AND d.status = 'Active'
            LIMIT 5
        """
        rows = await self._fetch(query, f"%{specialty.lower()}%")
        return [row["name"] for row in rows]

    # --- Availability ---

    async def get_doctor_details(self, doctor_name: str) -> Optional[Dict[str, Any]]:
        """Get ID and name of a doctor."""
        query = """
            SELECT doc_id, name 
            FROM doctor 
            WHERE LOWER(name) LIKE $1 AND status = 'Active' 
            LIMIT 1
        """
        return await self._fetchrow(query, f"%{doctor_name.lower()}%")

    async def get_doctor_shift(self, doc_id: int, day_name: str) -> Optional[Dict[str, Any]]:
        """Get shift for a doctor on a specific weekday."""
        query = """
            SELECT start_time, end_time 
            FROM doc_shift 
            WHERE doc_id = $1 AND day_of_week::text = $2 AND status = 'Active'
        """
        # Note: Casting day_of_week enum to text for comparison might be needed depending on driver
        # But asyncpg handles enums well if they match. We try string match first.
        return await self._fetchrow(query, doc_id, day_name)

    async def get_doctor_bookings(self, doc_id: int, date_val: date) -> List[datetime]:
        """Get all booked slot times for a doctor on a specific date."""
        query = """
            SELECT date_time 
            FROM appointment 
            WHERE doc_id = $1 AND DATE(date_time) = $2 
            AND app_status NOT IN ('Cancelled', 'NoShow', 'Rescheduled')
        """
        rows = await self._fetch(query, doc_id, date_val)
        return [row["date_time"] for row in rows]

    async def get_all_doctor_shifts(self, doc_id: int) -> List[Dict[str, Any]]:
        """Get all active shifts for a doctor, ordered by weekday."""
        query = """
            SELECT day_of_week, start_time, end_time 
            FROM doc_shift 
            WHERE doc_id = $1 AND status = 'Active'
            ORDER BY CASE day_of_week::text
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END
        """
        return await self._fetch(query, doc_id)

    # --- Booking Transaction ---

    async def ensure_patient_account(self, mobile_no: str) -> int:
        """Get or create patient account. Returns account_id."""
        # Check existing
        row = await self._fetchrow("SELECT account_id FROM patient_account WHERE mobile_no = $1", mobile_no)
        if row:
            return row["account_id"]
        
        # Create new
        await self._execute("INSERT INTO patient_account (mobile_no) VALUES ($1) ON CONFLICT DO NOTHING", mobile_no)
        row = await self._fetchrow("SELECT account_id FROM patient_account WHERE mobile_no = $1", mobile_no)
        return row["account_id"]

    async def ensure_patient(self, account_id: int, name: str, gender: Optional[str] = None, dob: Optional[date] = None) -> int:
        """Get or create patient. Returns pt_id."""
        query = "SELECT pt_id FROM patient WHERE account_id = $1 AND LOWER(name) = $2"
        row = await self._fetchrow(query, account_id, name.lower())
        if row:
            return row["pt_id"]
            
        # Create
        insert_query = """
            INSERT INTO patient (account_id, name, gender, dob) 
            VALUES ($1, $2, $3, $4)
            RETURNING pt_id
        """
        # We need to execute and get return value. _execute only returns status string usually.
        # So we use direct pool access for RETURNING
        try:
            async with self.memory_service._pool.acquire() as conn:
                pt_id = await conn.fetchval(insert_query, account_id, name, gender, dob)
                return pt_id
        except Exception as e:
            logger.error(f"Error creating patient: {e}")
            raise e

    async def create_appointment(self, account_id: int, pt_id: int, doc_id: int, reason: str, dt: datetime) -> Optional[int]:
        """Insert new appointment. Returns app_id on success, None on failure."""
        query = """
            INSERT INTO appointment (account_id, pt_id, doc_id, reason, date_time, app_status) 
            VALUES ($1, $2, $3, $4, $5, 'Booked')
            RETURNING app_id
        """
        if not self.memory_service._pool:
            if self.memory_service.is_enabled:
                await self.memory_service.initialize()
            if not self.memory_service._pool:
                logger.error("Database pool not available for appointment creation")
                return None
        
        try:
            async with self.memory_service._pool.acquire() as conn:
                app_id = await conn.fetchval(query, account_id, pt_id, doc_id, reason, dt)
                logger.info(f"Created appointment {app_id} for patient {pt_id} with doctor {doc_id}")
                return app_id
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return None

    # --- Manage Appointments ---

    async def find_upcoming_appointments(self, mobile_no: str) -> List[Dict[str, Any]]:
        """Find upcoming appointments for a mobile number."""
        query = """
            SELECT a.app_id, p.name as pt_name, d.name as doc_name, a.date_time
            FROM appointment a
            JOIN patient_account pa ON a.account_id = pa.account_id
            JOIN patient p ON a.pt_id = p.pt_id
            JOIN doctor d ON a.doc_id = d.doc_id
            WHERE pa.mobile_no = $1 
              AND a.date_time >= NOW() 
              AND a.app_status = 'Booked'
            ORDER BY a.date_time ASC
            LIMIT 5
        """
        return await self._fetch(query, mobile_no)

    async def update_appointment(self, app_id: int, new_doc_id: int, new_dt: datetime) -> str:
        """Reschedule appointment."""
        query = "UPDATE appointment SET doc_id = $1, date_time = $2, app_status = 'Rescheduled' WHERE app_id = $3"
        return await self._execute(query, new_doc_id, new_dt, app_id)

    async def cancel_appointment_by_id(self, app_id: int) -> str:
        """Cancel appointment."""
        query = "UPDATE appointment SET app_status = 'Cancelled' WHERE app_id = $1"
        return await self._execute(query, app_id)

# Singleton access
_hospital_service: Optional[HospitalService] = None

def get_hospital_service() -> HospitalService:
    global _hospital_service
    if _hospital_service is None:
        _hospital_service = HospitalService()
    return _hospital_service
