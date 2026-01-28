"""
Salon Service - Database operations for Salon Voice Agent

Provides all database interactions for:
- Services lookup
- Stylist search
- Availability checking
- Booking management
- Customer handling

Uses singleton pattern and shares the connection pool from MemoryService.
"""

import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any, Tuple
from memory.service import get_memory_service

logger = logging.getLogger("salon-service")


class SalonService:
    """
    Service for interacting with the salon-specific tables in the database.
    (Customers, Services, Stylists, Bookings, etc.)
    
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

    async def _fetchval(self, query: str, *args) -> Any:
        """Helper to fetch a single value."""
        if not self.memory_service._pool:
            if self.memory_service.is_enabled:
                await self.memory_service.initialize()
            if not self.memory_service._pool:
                return None
                
        try:
            async with self.memory_service._pool.acquire() as conn:
                return await conn.fetchval(query, *args)
        except Exception as e:
            logger.error(f"DB FetchVal Error: {e} | Query: {query}")
            return None

    # --- Service Search ---

    async def get_services(self, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search services by name keyword. Returns all active services if no term provided.
        Returns: List of {name, price, duration_minutes, description}
        """
        if search_term:
            query = """
                SELECT name, price, duration_minutes, description
                FROM services
                WHERE is_active = TRUE AND LOWER(name) LIKE $1
                ORDER BY name
            """
            return await self._fetch(query, f"%{search_term.lower()}%")
        else:
            query = """
                SELECT name, price, duration_minutes, description
                FROM services
                WHERE is_active = TRUE
                ORDER BY name
            """
            return await self._fetch(query)

    async def get_service_details(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service ID and details by name."""
        query = """
            SELECT service_id, name, price, duration_minutes, description
            FROM services
            WHERE is_active = TRUE AND LOWER(name) LIKE $1
            LIMIT 1
        """
        return await self._fetchrow(query, f"%{service_name.lower()}%")

    # --- Stylist Search ---

    async def get_stylists_for_service(self, service_name: str) -> List[Dict[str, Any]]:
        """
        Find all active stylists who can perform a specific service.
        Returns: List of {stylist_id, stylist_name, service_name}
        """
        query = """
            SELECT st.stylist_id, st.name AS stylist_name, sv.name AS service_name
            FROM stylists st
            JOIN stylist_services ss ON st.stylist_id = ss.stylist_id
            JOIN services sv ON ss.service_id = sv.service_id
            WHERE st.is_active = TRUE 
              AND sv.is_active = TRUE 
              AND LOWER(sv.name) LIKE $1
            ORDER BY st.name
        """
        return await self._fetch(query, f"%{service_name.lower()}%")

    async def get_stylists_for_multiple_services(self, service_names: List[str]) -> List[Dict[str, Any]]:
        """
        Find stylists who can perform ALL of the specified services.
        Returns: List of {stylist_id, stylist_name}
        """
        if not service_names:
            return []

        # This query finds stylists who have a count of matching services equal to the number of requested services
        # We need to construct the WHERE clause dynamically or use arrays
        
        # Using a simpler approach: multiple INTERSECTs or GROUP BY with HAVING count
        
        # Create placeholders for the IN clause ($1, $2, ...)
        placeholders = ",".join([f"${i+1}" for i in range(len(service_names))])
        
        query = f"""
            SELECT st.stylist_id, st.name AS stylist_name
            FROM stylists st
            JOIN stylist_services ss ON st.stylist_id = ss.stylist_id
            JOIN services sv ON ss.service_id = sv.service_id
            WHERE st.is_active = TRUE 
              AND sv.is_active = TRUE
              AND LOWER(sv.name) IN ({placeholders})
            GROUP BY st.stylist_id, st.name
            HAVING COUNT(DISTINCT sv.name) >= {len(service_names)}
            ORDER BY st.name
        """
        
        # Lowercase all service names
        args = [s.lower() for s in service_names]
        
        return await self._fetch(query, *args)

    async def get_stylist_details(self, stylist_name: str) -> Optional[Dict[str, Any]]:
        """Get stylist ID, name, and bio by name."""
        query = """
            SELECT stylist_id, name, bio, specialization, experience_years
            FROM stylists
            WHERE is_active = TRUE AND LOWER(name) LIKE $1
            LIMIT 1
        """
        return await self._fetchrow(query, f"%{stylist_name.lower()}%")

    async def get_all_stylists(self) -> List[Dict[str, Any]]:
        """Get all active stylists."""
        query = """
            SELECT stylist_id, name, bio, specialization, experience_years
            FROM stylists
            WHERE is_active = TRUE
            ORDER BY name
        """
        return await self._fetch(query)

    # --- Salon Hours ---

    async def get_salon_hours(self, weekday: str) -> Optional[Dict[str, Any]]:
        """
        Get salon hours for a specific weekday.
        weekday: lowercase day name like 'monday', 'tuesday', etc.
        Returns: {open_time, close_time, is_closed}
        """
        query = """
            SELECT open_time, close_time, is_closed
            FROM salon_hours
            WHERE day_of_week = $1::weekday
        """
        return await self._fetchrow(query, weekday.lower())

    # --- Stylist Availability ---

    async def get_stylist_availability(self, stylist_id: int, date_val: date) -> Optional[Dict[str, Any]]:
        """
        Get stylist's working hours for a specific date.
        Returns: {start_time, end_time} or None if not working
        """
        query = """
            SELECT start_time, end_time
            FROM stylist_availability
            WHERE stylist_id = $1 AND date = $2
        """
        return await self._fetchrow(query, stylist_id, date_val)

    async def get_stylist_bookings(self, stylist_id: int, date_val: date) -> List[Dict[str, Any]]:
        """
        Get all bookings for a stylist on a specific date.
        Used for conflict checking.
        Returns: List of {booking_id, start_time, end_time, status}
        """
        query = """
            SELECT booking_id, start_time, end_time, status
            FROM bookings
            WHERE stylist_id = $1 
              AND booking_date = $2 
              AND status IN ('confirmed', 'pending')
            ORDER BY start_time
        """
        return await self._fetch(query, stylist_id, date_val)

    # --- Customer Management ---

    async def ensure_customer(self, name: str, phone: str) -> int:
        """
        Get or create a customer by phone number.
        Returns: customer_id
        """
        # Try to find existing customer
        existing = await self._fetchrow(
            "SELECT customer_id FROM customers WHERE phone_number = $1",
            phone
        )
        if existing:
            return existing["customer_id"]
        
        # Create new customer
        customer_id = await self._fetchval(
            """
            INSERT INTO customers (name, phone_number)
            VALUES ($1, $2)
            RETURNING customer_id
            """,
            name, phone
        )
        return customer_id

    async def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get customer details by phone number."""
        query = """
            SELECT customer_id, name, phone_number, email
            FROM customers
            WHERE phone_number = $1
        """
        return await self._fetchrow(query, phone)

    # --- Booking Operations ---

    async def create_booking(
        self,
        customer_id: int,
        stylist_id: int,
        service_id: int,
        booking_date: date,
        start_time: time,
        end_time: time,
        notes: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a new booking.
        Returns: booking_id on success, None on failure
        """
        query = """
            INSERT INTO bookings 
                (customer_id, stylist_id, service_id, booking_date, start_time, end_time, status, notes)
            VALUES ($1, $2, $3, $4, $5, $6, 'confirmed', $7)
            RETURNING booking_id
        """
        return await self._fetchval(
            query, customer_id, stylist_id, service_id, 
            booking_date, start_time, end_time, notes
        )

    async def find_customer_bookings(self, phone: str) -> List[Dict[str, Any]]:
        """
        Find all active bookings for a customer by phone number.
        Returns: List of {booking_id, service_name, stylist_name, booking_date, start_time, end_time, status}
        """
        query = """
            SELECT b.booking_id, sv.name AS service_name, st.name AS stylist_name,
                   b.booking_date, b.start_time, b.end_time, b.status
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            LEFT JOIN services sv ON b.service_id = sv.service_id
            LEFT JOIN stylists st ON b.stylist_id = st.stylist_id
            WHERE c.phone_number = $1 
              AND b.status IN ('confirmed', 'pending')
              AND b.booking_date >= CURRENT_DATE
            ORDER BY b.booking_date, b.start_time
        """
        return await self._fetch(query, phone)

    async def cancel_booking(self, booking_id: int, reason: Optional[str] = None) -> bool:
        """
        Cancel a booking by ID.
        Returns: True on success
        """
        query = """
            UPDATE bookings 
            SET status = 'cancelled', cancellation_reason = $2
            WHERE booking_id = $1
        """
        result = await self._execute(query, booking_id, reason)
        return "UPDATE" in result

    async def reschedule_booking(
        self,
        booking_id: int,
        new_date: date,
        new_start_time: time,
        new_end_time: time,
        new_stylist_id: Optional[int] = None
    ) -> bool:
        """
        Reschedule a booking to a new date/time.
        Optionally change the stylist.
        Returns: True on success
        """
        if new_stylist_id:
            query = """
                UPDATE bookings 
                SET booking_date = $2, start_time = $3, end_time = $4, stylist_id = $5
                WHERE booking_id = $1
            """
            result = await self._execute(query, booking_id, new_date, new_start_time, new_end_time, new_stylist_id)
        else:
            query = """
                UPDATE bookings 
                SET booking_date = $2, start_time = $3, end_time = $4
                WHERE booking_id = $1
            """
            result = await self._execute(query, booking_id, new_date, new_start_time, new_end_time)
        return "UPDATE" in result

    async def check_slot_available(
        self,
        stylist_id: int,
        booking_date: date,
        start_time: time,
        end_time: time,
        exclude_booking_id: Optional[int] = None
    ) -> bool:
        """
        Check if a time slot is available for a stylist.
        Returns: True if no conflicting bookings exist
        """
        if exclude_booking_id:
            query = """
                SELECT COUNT(*) as cnt
                FROM bookings
                WHERE stylist_id = $1 
                  AND booking_date = $2
                  AND status IN ('confirmed', 'pending')
                  AND booking_id != $5
                  AND start_time < $4 
                  AND end_time > $3
            """
            result = await self._fetchrow(query, stylist_id, booking_date, start_time, end_time, exclude_booking_id)
        else:
            query = """
                SELECT COUNT(*) as cnt
                FROM bookings
                WHERE stylist_id = $1 
                  AND booking_date = $2
                  AND status IN ('confirmed', 'pending')
                  AND start_time < $4 
                  AND end_time > $3
            """
            result = await self._fetchrow(query, stylist_id, booking_date, start_time, end_time)
        
        return result["cnt"] == 0 if result else True

    async def get_slots_in_range(
        self,
        booking_date: date,
        start_range: time,
        end_range: time,
        duration_minutes: int,
        stylist_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find available start times for a given duration within a specific time range.
        If stylist_id is None, checks all active stylists.
        
        Returns: List of {stylist_id, stylist_name, start_time}
        """
        
        # This is a more complex query. We need to:
        # 1. Find working stylists for that day
        # 2. Check their shift overlap with the requested range
        # 3. Subtract existing bookings
        # 4. Return valid start times (simplified to 30 min intervals for the agent)
        
        # For the agent's purpose, we'll return open slots.
        # We can fetch keeping it simple: Fetch shifts and bookings, then compute in Python
        # DB-side slot computation is hard with generic intervals.
        
        query_shifts = """
            SELECT sa.stylist_id, s.name as stylist_name, sa.start_time, sa.end_time
            FROM stylist_availability sa
            JOIN stylists s ON sa.stylist_id = s.stylist_id
            WHERE sa.date = $1 AND s.is_active = TRUE
        """
        args = [booking_date]
        if stylist_id:
            query_shifts += " AND sa.stylist_id = $2"
            args.append(stylist_id)
            
        shifts = await self._fetch(query_shifts, *args)
        if not shifts:
            return []
            
        # Get all bookings for these stylists on this day
        stylist_ids = [s['stylist_id'] for s in shifts]
        if not stylist_ids:
            return []
            
        placeholders = ",".join([f"${i+2}" for i in range(len(stylist_ids))])
        query_bookings = f"""
            SELECT stylist_id, start_time, end_time
            FROM bookings
            WHERE booking_date = $1 
              AND status IN ('confirmed', 'pending')
              AND stylist_id IN ({placeholders})
            ORDER BY start_time
        """
        
        bookings = await self._fetch(query_bookings, booking_date, *stylist_ids)
        
        # Compute availability in Python
        available_slots = []
        
        # Group bookings by stylist
        bookings_by_stylist = {}
        for b in bookings:
            sid = b['stylist_id']
            if sid not in bookings_by_stylist:
                bookings_by_stylist[sid] = []
            bookings_by_stylist[sid].append(b)
            
        # Helper to check if a slot overlaps with any booking
        def is_overlapped(s_id, start, end):
            for b in bookings_by_stylist.get(s_id, []):
                # Overlap logic: (StartA < EndB) and (EndA > StartB)
                if start < b['end_time'] and end > b['start_time']:
                    return True
            return False

        # Iterate through shifts and generate 30-min slots
        for shift in shifts:
            s_id = shift['stylist_id']
            s_name = shift['stylist_name']
            
            # Effective range: intersection of shift and requested range
            eff_start = max(shift['start_time'], start_range)
            eff_end = min(shift['end_time'], end_range)
            
            if eff_start >= eff_end:
                continue
                
            # Iterate in 15 or 30 minute increments
            current = datetime.combine(booking_date, eff_start)
            limit = datetime.combine(booking_date, eff_end)
            
            while current + timedelta(minutes=duration_minutes) <= limit:
                slot_start = current.time()
                slot_end = (current + timedelta(minutes=duration_minutes)).time()
                
                if not is_overlapped(s_id, slot_start, slot_end):
                    available_slots.append({
                        "stylist_id": s_id,
                        "stylist_name": s_name,
                        "start_time": slot_start
                    })
                
                # Increment by 30 mins
                current += timedelta(minutes=30)
                
        return available_slots


# Singleton access
_salon_service: Optional[SalonService] = None


def get_salon_service() -> SalonService:
    """Get the singleton SalonService instance."""
    global _salon_service
    if _salon_service is None:
        _salon_service = SalonService()
    return _salon_service
