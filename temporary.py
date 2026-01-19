
"""
main.py - LLM Server (UPDATED WITH MEMORY)
Re-implements the Salon Agent logic using LangGraph.
Stores conversation history in memory so the agent remembers previous details.
Adds a confirmation step: The agent collects details -> Shows Preview -> Waits for "Yes" -> Saves to DB.
"""

from calendar import calendar
import os
import re
import logging
import asyncio
from datetime import datetime, timedelta, time
from typing import List, Optional, Annotated, TypedDict, Dict

import asyncpg
from dateutil import parser, relativedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uvicorn import run

# LangChain & LangGraph Imports
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from datetime import datetime, timedelta, time, date

# --- Configuration ---

# DATABASE CONFIGURATION
# Replace with your actual database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:nirmal%40123@localhost:5432/salon_receptionist")

# OPENAI API KEY CONFIGURATION
# OPTION 1: Paste your key here directly (Easiest for local testing)
#
OPENAI_API_KEY = "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"


# OPTION 2: Use Environment Variable
if not 'OPENAI_API_KEY' in locals() or not OPENAI_API_KEY:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# VALIDATION
if not OPENAI_API_KEY:
    print("-" * 60)
    print("CRITICAL ERROR: OPENAI_API_KEY is missing!")
    print("Please set the API key in main.py or environment variables.")
    print("-" * 60)
    raise ValueError(
        "OpenAI API Key is missing. Please check main.py configuration.")

app = FastAPI()

# --- In-Memory Session Store ---
# Stores conversation history for each session ID.
# Key: session_id (str)
# Value: List[Messages] (The conversation history)
# NOTE: This memory is temporary. If the server restarts, history is lost.
session_memory: Dict[str, List] = {}

# --- Database Setup ---


class SalonDB:
    """Manages the connection pool for the salon agent."""
    _pool = None

    @classmethod
    async def get_pool(cls):
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=10.0
            )
        return cls._pool


async def _execute_query(query: str, *args):
    pool = await SalonDB.get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def _execute_command(command: str, *args):
    pool = await SalonDB.get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(command, *args)


def _combine_date_time(date_obj: date, time_str: str) -> datetime:
    """Combines a date object and a time string (HH:MM) into a datetime object."""
    # Safety check: Ensure we have a date object, not datetime
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()

    try:
        hours, minutes = map(int, time_str.split(":"))
    except ValueError:
        # Handle case where time might not be in HH:MM format
        hours = int(time_str)
        minutes = 0

    return datetime.combine(date_obj, time(hour=hours, minute=minutes))


def _build_requested_slot(
    booking_date: date,
    preferred_start_time: str,
    duration_minutes: int
):
    """Builds the start and end datetime for the requested slot."""
    start_dt = _combine_date_time(booking_date, preferred_start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return start_dt, end_dt


def _is_slot_available(
    requested_start: datetime,
    requested_end: datetime,
    bookings: List
) -> bool:
    """
    Returns False if requested slot overlaps with ANY existing booking.
    """
    for booking in bookings:
        # Combine DB date (date) with DB time (time) to create a datetime
        booked_start = datetime.combine(
            booking["booking_date"],
            booking["start_time"]
        )
        booked_end = datetime.combine(
            booking["booking_date"],
            booking["end_time"]
        )

        # Overlap condition: Start < ExistingEnd AND End > ExistingStart
        if requested_start < booked_end and requested_end > booked_start:
            return False

    return True


async def _get_salon_hours(
    date_obj: date,
    preferred_start_time: str
) -> Optional[str]:
    """
    Checks salon open/close status and validates preferred time.
    Returns None if valid, or an error string if closed/invalid.
    """
    query = """
        SELECT open_time, close_time, is_closed
        FROM salon_hours
        WHERE day_of_week = $1
    """

    try:
        # Use global _execute_query, not self._execute_query
        rows = await _execute_query(query, date_obj.weekday())

        if not rows:
            return "❌ Salon hours not configured for this day."

        row = rows[0]

        # 1. Check if salon is closed (e.g., Sunday)
        if row["is_closed"] or row["open_time"] is None or row["close_time"] is None:
            return "❌ The salon is closed on this day."

        open_time = row["open_time"]
        close_time = row["close_time"]

        # 2. Validate preferred time
        # Handle input like "14:00" or "2:00 PM"
        try:
            # Try parsing strict HH:MM first
            preferred_time = datetime.strptime(
                preferred_start_time, "%H:%M").time()
        except ValueError:
            try:
                # Try parsing with AM/PM
                preferred_time = datetime.strptime(
                    preferred_start_time, "%I:%M %p").time()
            except ValueError:
                return f"⚠️ I couldn't understand the time format: '{preferred_start_time}'."

        if not (open_time <= preferred_time < close_time):
            return (
                f"❌ The salon is open from "
                f"{open_time.strftime('%I:%M %p')} to {close_time.strftime('%I:%M %p')}. "
                f"Please choose a time within these hours."
            )

        # 3. All checks passed
        return None

    except Exception as e:
        print(f"Error fetching salon hours: {e}")
        return "⚠️ Unable to verify salon hours right now."


def _parse_natural_date(date_str: str) -> Optional[datetime]:
    today = datetime.now()
    lower_str = date_str.lower().strip()
    if lower_str == "tomorrow":
        return today + timedelta(days=1)
    elif lower_str == "today":
        return today
    try:
        parsed = parser.parse(date_str, fuzzy=True, default=today)
        return parsed
    except Exception:
        return None


@tool
async def handle_non_booking_query(query_text: str) -> str:
    """
    Handles general questions (pricing, services, stylists).
    """
    query_lower = query_text.lower()

    if any(keyword in query_lower for keyword in ["service", "offer", "menu", "price", "cost", "how much"]):
        try:
            rows = await _execute_query(
                "SELECT name, price, duration_minutes FROM services WHERE is_active = TRUE ORDER BY name"
            )
            if not rows:
                return "We couldn't find any active services."

            for row in rows:
                if row['name'].lower() in query_lower:
                    return f"Our {row['name']} costs ${row['price']} and takes about {row['duration_minutes']} minutes."

            services_list = [
                f"{row['name']} (₹{row['price']})" for row in rows[:7]]
            return "Here are our services: " + ", ".join(services_list) + "."
        except Exception as e:
            return f"Error accessing services: {e}"

    elif any(keyword in query_lower for keyword in ["stylist", "staff", "who works", "hairdresser"]):
        try:
            rows = await _execute_query(
                "SELECT name, experience_years FROM stylists WHERE is_active = TRUE ORDER BY name"
            )
            if not rows:
                return "No stylists listed."

            stylists_info = [f"{row['name']}" for row in rows]
            return "Our team includes: " + ", ".join(stylists_info) + "."
        except Exception as e:
            return f"Error loading staff: {e}"

    elif any(keyword in query_lower for keyword in ["location", "address", "where"]):
        return "We are located at 123 Beauty Lane, Downtown."

    return "I can help you with booking appointments. Are you looking to schedule something?"


@tool
async def search_services(search_term: str = "") -> str:
    """
    Search for services in the database for booking purposes.
    Handles single service requests (e.g., 'haircut') or multiple 
    requests (e.g., 'haircut and facial').

    Returns: Name, Price, and Duration for all matched services.
    """
    def get_search_terms(text):
        if not text:
            return []
        cleaned = text.lower()
        terms = []
        for part in re.split(r'\s+and\s+|\s*,\s*|\s*\+\s*|\s*&\s+', cleaned):
            if part.strip():
                terms.append(part.strip())
        return terms

    try:
        found_services = []
        not_found_terms = []

        if search_term:
            terms = get_search_terms(search_term)

            for term in terms:
                # Removed ORDER BY name to preserve input order and DB natural order
                query = """
                    SELECT name, price, duration_minutes 
                    FROM services 
                    WHERE is_active = TRUE AND LOWER(name) LIKE $1
                """
                rows = await _execute_query(query, f"%{term}%")
                if rows:
                    found_services.extend(rows)
                else:
                    not_found_terms.append(term)

            unique_services = []
            seen_names = set()
            for row in found_services:
                if row['name'] not in seen_names:
                    unique_services.append(row)
                    seen_names.add(row['name'])
            found_services = unique_services

        else:
            query = "SELECT name, price, duration_minutes FROM services WHERE is_active = TRUE ORDER BY name"
            found_services = await _execute_query(query)

        if not found_services:
            return f"I couldn't find any services matching '{search_term}'. Would you like to see a list of all our services?"

        if found_services and not_found_terms:
            response = (
                f"I couldn't find these service(s): {', '.join(not_found_terms)}.\n\n"
                "However, I found the following available service(s):\n"
            )
            for s in found_services:
                response += f"- {s['name']}: ${s['price']} ({s['duration_minutes']} mins)\n"

            response += "\nWould you like to book one of these?"
            return response.strip()

        if len(found_services) == 1:
            s = found_services[0]
            return (f"I found the service '{s['name']}' for your booking.\n"
                    f"Price: ${s['price']} | Duration: {s['duration_minutes']} mins.\n"
                    f"Shall I proceed with booking this?")

        response = "I found the following services for your request:\n"
        for s in found_services:
            response += f"- {s['name']}: ${s['price']} ({s['duration_minutes']} mins)\n"

        if search_term:
            response += "\nPlease confirm which of these you would like to book, or say 'all' if you want them all."
        else:
            response += "\nWhich one would you like to book?"

        return response.strip()

    except Exception as e:
        return "I'm having trouble accessing our service list right now. Please try again later."


@tool
async def get_stylists_for_services(
    service_names: Annotated[List[str],
                             "List of service names the user wants (e.g. ['Haircut', 'Facial'])"]
) -> str:
    """
    Finds stylists for requested services efficiently.
    """
    if not service_names:
        return "Please specify which services you are interested in."

    try:
        patterns = [f"%{s.lower()}%" for s in service_names]

        query = """
            SELECT
                sv.service_id,
                sv.name       AS service_name,
                st.stylist_id,
                st.name       AS stylist_name
            FROM services sv
            JOIN stylist_services ss
                ON ss.service_id = sv.service_id
            JOIN stylists st
                ON st.stylist_id = ss.stylist_id
            WHERE sv.is_active = TRUE
            AND st.is_active = TRUE
            AND LOWER(sv.name) ILIKE ANY($1)
        """
        # ORDER BY sv.name, st.name

        rows = await _execute_query(query, patterns)

        if not rows:
            return f"I couldn't find any services or stylists matching '{', '.join(service_names)}'."

        service_map = {}

        for row in rows:
            s_name = row['service_name']
            st_name = row['stylist_name']

            if s_name not in service_map:
                service_map[s_name] = []

            if st_name not in service_map[s_name]:
                service_map[s_name].append(st_name)

        found_services = list(service_map.keys())

        if len(found_services) == 1:
            svc_name = found_services[0]
            stylists = service_map[svc_name]

            return (f"For **{svc_name}**, the following stylists are available: {', '.join(stylists)}.\n"
                    f"Who would you like to book for the {svc_name}?")

        else:
            intro = f"I found options for: {', '.join(found_services)}. Let's book them one by one.\n"

            first_svc = found_services[0]
            first_stylists = service_map[first_svc]

            question = (
                f"First, for **{first_svc}**, the available stylists are: {', '.join(first_stylists)}.\n"
                f"Who would you like to perform the {first_svc}?"
            )

            return intro + question

    except Exception as e:
        return "I had trouble checking which stylists provide those services."


@tool
async def get_customer_bookings(phone_number: Annotated[str, "Customer's 10-digit phone number"]) -> str:
    """
    Retrieves all active (CONFIRMED or PENDING) bookings for a specific phone number.
    Used to initiate Reschedule or Cancel workflows.
    """
    query = """
        SELECT b.booking_id, b.booking_date, b.start_time, b.end_time, b.status,
               s.name AS service_name, st.name AS stylist_name, c.name AS customer_name
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN services s ON b.service_id = s.service_id
        JOIN stylists st ON b.stylist_id = st.stylist_id
        WHERE c.phone_number = $1 AND b.status IN ('CONFIRMED', 'PENDING')
        ORDER BY b.booking_date, b.start_time
    """
    try:
        rows = await _execute_query(query, phone_number)
        if not rows:
            return f"No active bookings found for phone number {phone_number}. Please check the number or book a new appointment."
        
        response = f"Found {len(rows)} booking(s) for {phone_number}:\n\n"
        for row in rows:
            response += (
                f"🔖 **Booking ID: {row['booking_id']}**\n"
                f"   Service: {row['service_name']}\n"
                f"   Stylist: {row['stylist_name']}\n"
                f"   Date: {row['booking_date']}\n"
                f"   Time: {row['start_time'].strftime('%I:%M %p')} - {row['end_time'].strftime('%I:%M %p')}\n\n"
            )
        response += "Please provide the **Booking ID** you wish to modify or cancel."
        return response
    except Exception as e:
        return f"Error fetching bookings: {e}"

@tool
async def cancel_booking_action(
    booking_id: Annotated[int, "The ID of the booking to cancel"]
) -> str:
    """
    Cancels a specific booking by setting its status to CANCELLED.
    """
    try:
        # Check if exists
        check = await _execute_query("SELECT booking_id FROM bookings WHERE booking_id = $1", booking_id)
        if not check:
            return f"Booking ID {booking_id} not found."
            
        await _execute_command("UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = $1", booking_id)
        return f"Booking ID {booking_id} has been successfully cancelled."
    except Exception as e:
        return f"Failed to cancel booking: {e}"

@tool
async def reschedule_booking_action(
    booking_id: Annotated[int, "The ID of the booking to reschedule"],
    stylist_name: Annotated[str, "Name of the new stylist (or same stylist)"],
    date_str: Annotated[str, "New date (YYYY-MM-DD)"],
    time_str: Annotated[str, "New start time (HH:MM AM/PM)"]
) -> str:
    """
    Updates the date, time, and stylist for an existing booking.
    NOTE: This function performs the update. Availability checks should be done BEFORE calling this tool
    using the 'check_availability_smart' tool.
    """
    try:
        # 1. Validate booking exists and get details
        booking_info = await _execute_query(
            "SELECT service_id, customer_id FROM bookings WHERE booking_id = $1", booking_id
        )
        if not booking_info:
            return f"Booking ID {booking_id} not found."
        
        service_id = booking_info[0]['service_id']
        customer_id = booking_info[0]['customer_id']

        # 2. Get Service Duration
        service_info = await _execute_query(
            "SELECT duration_minutes FROM services WHERE service_id = $1", service_id
        )
        duration = service_info[0]['duration_minutes']

        # 3. Get Stylist ID
        stylist_res = await _execute_query(
            "SELECT stylist_id FROM stylists WHERE LOWER(name) LIKE $1", f"%{stylist_name.lower()}%"
        )
        if not stylist_res:
            return f"Stylist '{stylist_name}' not found."
        stylist_id = stylist_res[0]['stylist_id']

        # 4. Parse Time
        try:
            booking_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            try:
                booking_time_obj = datetime.strptime(time_str, "%I:%M %p").time()
            except ValueError:
                booking_time_obj = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            return "Invalid Date or Time format provided."

        # 5. Calculate End Time
        start_dt = datetime.combine(booking_date_obj, booking_time_obj)
        end_dt = start_dt + timedelta(minutes=duration)
        end_time_obj = end_dt.time()

        # 6. Double Check Availability (Safety Lock)
        # We verify once more inside the transaction to be safe
        conflict_check = await _execute_query(
            """
            SELECT COUNT(*) as cnt FROM bookings 
            WHERE stylist_id = $1 AND booking_date = $2 
            AND status IN ('CONFIRMED', 'PENDING')
            AND booking_id != $3 
            AND start_time < $4 AND end_time > $5
            """,
            stylist_id, booking_date_obj, booking_id, end_time_obj, booking_time_obj
        )

        if conflict_check[0]['cnt'] > 0:
            return "❌ ERROR: That slot was just booked! Please choose a different time."

        # 7. Execute Update
        await _execute_command(
            """
            UPDATE bookings 
            SET stylist_id = $1, booking_date = $2, start_time = $3, end_time = $4 
            WHERE booking_id = $5
            """,
            stylist_id, booking_date_obj, booking_time_obj, end_time_obj, booking_id
        )

        return (
            f"✅ Booking Rescheduled Successfully!\n"
            f"New Details:\n"
            f"- Date: {booking_date_obj}\n"
            f"- Time: {booking_time_obj.strftime('%I:%M %p')}\n"
            f"- Stylist: {stylist_name}"
        )

    except Exception as e:
        return f"Error rescheduling booking: {e}"

# --- EXISTING TOOLS (Modified only if needed) ---


@tool
async def check_availability_smart(
    stylist_name: Annotated[str, "The name of the stylist"],
    date_str: Annotated[str, "The date (e.g. 'Tomorrow', '2024-01-10')"],
    total_duration_minutes: Annotated[int, "Total duration of all services combined"],
    preferred_start_time: Annotated[Optional[str],
                                    "Specific time (e.g. '14:00') or Approximate (e.g. '11:00')"] = None,
    window_start_time: Annotated[Optional[str],
                                 "Start of search window (HH:MM) for range queries"] = None,
    window_end_time: Annotated[Optional[str],
                               "End of search window (HH:MM) for range queries"] = None
) -> str:
    """
    Performs advanced availability checking using the verified standalone logic.
    Checks availability.
    - If 'preferred_start_time' is given, checks that specific slot.
    - If 'preferred_start_time' is EMPTY (User asks to suggest), finds the earliest available slot in the shift (or window).

    """
    try:
        # 1️⃣ Parse date
        booking_date = _parse_natural_date(date_str)
        if not booking_date:
            return "❌ Invalid booking date."

         # 2. CHECK SALON HOURS (New Step)
        # We must have a time to check if the salon is open.
        if not preferred_start_time:
            return "⚠️ Please provide a preferred start time so I can check if we are open."

        salon_check = await _get_salon_hours(booking_date, preferred_start_time)

        # If salon_check returns a string (error message), return it immediately
        if salon_check:
            return salon_check

            # ✅ Stylist shift validation
        stylist_shift_error = await _check_stylist_shift(
            stylist_id,
            stylist_name,
            booking_date,
            preferred_start_time
        )
        logging.debug(f"Stylist Shift Check: {stylist_shift_error}")

        if stylist_shift_error:
            return stylist_shift_error

        # 2️⃣ Get stylist (QUERY)
        stylist_query = """
            SELECT stylist_id, name
            FROM stylists
            WHERE LOWER(name) LIKE $1
              AND is_active = TRUE
        """
        # NOTE: Use 'await _execute_query', NOT 'self._execute_query'
        stylists = await _execute_query(
            stylist_query,
            f"%{stylist_name.lower()}%"
        )

        if not stylists:
            return f"❌ Stylist '{stylist_name}' not found."

        stylist_id = stylists[0]["stylist_id"]

        # 3️⃣ Get bookings (QUERY)
        booking_query = """
            SELECT
                booking_id,
                booking_date,
                start_time,
                end_time
            FROM bookings
            WHERE stylist_id = $1
              AND booking_date = $2
              AND status = 'CONFIRMED'
            ORDER BY start_time
        """

        bookings = await _execute_query(
            booking_query,
            stylist_id,
            booking_date
        )

        # 4️⃣ Preferred time required
        if not preferred_start_time:
            return "⚠️ Please provide a preferred start time."

        # 5️⃣ Build requested time slot
        # Use standalone helper, NOT self._build_requested_slot
        requested_start, requested_end = _build_requested_slot(
            booking_date,
            preferred_start_time,
            total_duration_minutes
        )

        # 6️⃣ Check availability
        # Use standalone helper, NOT self._is_slot_available
        if not _is_slot_available(
            requested_start,
            requested_end,
            bookings
        ):
            return (
                f"❌ Slot already booked "
                f"from {requested_start.time()} to {requested_end.time()}."
            )

        return (
            f"✅ Slot available "
            f"from {requested_start.time()} to {requested_end.time()}."
        )

    except Exception as e:
        import traceback
        traceback.print_exc()  # Print error to console for debugging
        return "I'm having trouble checking the availability right now."

# --- NEW TOOL: Preview Booking ---


@tool
async def preview_booking_details(
    stylist_name: Annotated[str, "Name of the stylist"],
    date_str: Annotated[str, "Date (YYYY-MM-DD)"],
    time_str: Annotated[str, "Time (HH:MM AM/PM)"],
    services: Annotated[List[str], "List of services included"],
    customer_name: Annotated[str, "Customer full name"],
    customer_phone: Annotated[str, "Customer phone number"]
) -> str:
    """
    Generates a summary of the booking details for the user to confirm.
    DOES NOT save to the database yet.
    Returns a compact string to avoid large text blocks.
    """
    service_list_str = ", ".join(services)

    # Compact format: No emojis, minimal spacing
    summary = (
        f"Please confirm booking for {customer_name}:\n"
        f"- Service: {service_list_str}\n"
        f"- Stylist: {stylist_name}\n"
        f"- Date: {date_str} at {time_str}\n"
        f"- Phone: {customer_phone}\n\n"
        f"Say 'Yes' to confirm or 'No' to change details."
    )
    return summary


@tool
async def create_booking(
    stylist_name: Annotated[str, "Name of the stylist"],
    date_str: Annotated[str, "Date (YYYY-MM-DD)"],
    time_str: Annotated[str, "Time (HH:MM AM/PM)"],
    services: Annotated[List[str], "List of services included"],
    customer_name: Annotated[str, "Customer full name"],
    customer_phone: Annotated[str, "Customer phone number"]
) -> str:
    """
    Saves the confirmed booking to the database.
    Call this ONLY after the user has confirmed the details via preview_booking_details.    """
    try:

        # ---- DATE ----
        try:
            booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return "I need the date in YYYY-MM-DD format."

        try:
            booking_time = datetime.strptime(time_str, "%I:%M %p").time()
        except ValueError:
            try:
                booking_time = datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                return "I couldn't understand the time format."

        stylist_res = await _execute_query("SELECT stylist_id FROM stylists WHERE LOWER(name) LIKE $1", f"%{stylist_name.lower()}%")
        if not stylist_res:
            return f"Stylist {stylist_name} not found."
        stylist_id = stylist_res[0]['stylist_id']

        pool = await SalonDB.get_pool()
        async with pool.acquire() as conn:
            # Simple Insert - Creates new ID every time regardless of duplicate phone.
            # NOTE: This requires that the 'phone_number' column does NOT have a UNIQUE constraint.
            customer_id = await conn.fetchval(
                """
                INSERT INTO customers (name, phone_number) 
                VALUES ($1, $2) 
                RETURNING customer_id
                """,
                customer_name, customer_phone
            )

        total_duration = 0
        service_ids = []

        for s_name in services:
            s_res = await _execute_query("SELECT service_id, duration_minutes FROM services WHERE LOWER(name) LIKE $1", f"%{s_name.lower()}%")
            if s_res:
                service_ids.append(s_res[0]['service_id'])
                total_duration += s_res[0]['duration_minutes']

        start_dt = datetime.combine(booking_date, booking_time)
        end_dt = start_dt + timedelta(minutes=total_duration)
        end_time = end_dt.time()

        conflict_count = await _execute_query(
            """
            SELECT COUNT(*) as cnt FROM bookings 
            WHERE stylist_id = $1 AND booking_date = $2 
            AND status IN ('CONFIRMED', 'PENDING')
            AND start_time < $3 AND end_time > $4
            """,
            stylist_id, booking_date, end_time, booking_time
        )

        if conflict_count[0]['cnt'] > 0:
            return "Oh no! Someone just booked that slot. That time is no longer available. Would you like to check a different time?"

        primary_service_id = service_ids[0] if service_ids else None

        if primary_service_id:
            await _execute_command(
                """
                INSERT INTO bookings (customer_id, stylist_id, service_id, booking_date, start_time, end_time, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'CONFIRMED')
                """,
                customer_id, stylist_id, primary_service_id, booking_date, booking_time, end_time
            )

            service_list_str = ", ".join(services)
            return (
                f"Your appointment is confirmed!\n"
                f"Services: {service_list_str}\n"
                f"Stylist: {stylist_name}\n"
                f"Date: {booking_date.strftime('%A, %B %d')}\n"
                f"Time: {booking_time.strftime('%I:%M %p')}\n"
                f"See you then!"
            )
        else:
            return "I couldn't verify the services for this booking."

    except Exception as e:
        return "There was a technical error saving your booking. Please try again."

# --- LangGraph Setup ---

SYSTEM_PROMPT = """You are an intelligent receptionist for Luxe Salon & Spa.

STRICT WORKFLOW RULES:
1. Greeting
2. Service Selection (Collect all services: Haircut, Facial, etc.)
3. Service–Stylist Mapping (Find stylists who can do ALL requested services)
4. Date & Time Selection (Collect Date and Time/Range)->
Whenever the user provides a DATE and TIME:
- You MUST call check_availability_smart.
- The tool will internally check salon_hours.
- The tool will automatically verify if the SALON is open.


Rules enforced by the tool:
1. SALON HOURS
- If the salon is CLOSED on that day (is_closed = true or no open/close time),
  you must inform the user that the salon is closed.
- If the salon is OPEN but the requested time is outside open_time and close_time,
  you must clearly tell the user the salon's operating hours and ask them to
  choose a time within that range.
- You MUST stop the flow until the user selects a valid time.


5. Availability Validation (Use check_availability_smart)
STYLIST SHIFT RULES:
- If a stylist_id or stylist_name is already identified:
   - The system MUST validate the stylist’s shift for the selected date and time.
- If the stylist is not working on that date:
   - Inform the user and ask for another date or stylist.
   - STOP the flow.
- If the stylist is working but not available at the requested time:
   - Ask the user to choose another time within the stylist’s shift.
   - STOP the flow.
- Proceed to slot finalization ONLY if the stylist is available at the requested time.

6. Slot Finalization
7. User Details Collection (Name, Phone)->PHONE NUMBER RULES:
- Always collect customer's phone number before booking.
- Phone number must be exactly 10 digits.
- Only numeric digits are allowed (no spaces, no symbols, no country code).
- If the phone number is invalid, politely ask the user to re-enter it.
- DO NOT call create_booking unless a valid phone number is provided.

8. Booking Preview (Use preview_booking_details)
9. Booking Confirmation (Use create_booking) ->ONLY call create_booking when confirmation is clearly positive words used by user (e.g., "Yes", "Confirm", "Book it").

CRITICAL BEHAVIORS:
- DO NOT proceed to the next step until the current step is satisfied.
- If the user provides info out of order (e.g. "I want to see Sarah tomorrow"), store it mentally but follow the workflow steps to validate previous steps (e.g. Check Service -> Stylist Mapping).
- GENERAL INQUIRIES: If the user asks general questions about services, stylists, pricing, or salon info, use the 'handle_non_booking_query' tool.
- LIMIT GENERAL CHAT: If the user asks 5 separate general questions without showing booking intent, politely end the call.
- TIME HANDLING (UPDATED): 
   - If the user gives a specific time (e.g., "2 PM"), use 'check_availability_smart' with 'preferred_start_time'.
   - If the user asks you to SUGGEST a time (e.g., "What time works?", "Suggest something", "I'm free anytime"), call 'check_availability_smart' WITHOUT 'preferred_start_time'. The tool will automatically find the earliest available slot.
- NEVER invent availability. Use the database tools.
- If multiple services are requested, book only if one stylist can do all services; otherwise inform the user that separate bookings are needed, show stylist options per service, book them one by one, and ask for name and phone number only once at the end before final confirmation.
- For "Approximate" times (e.g. "around 11am"), define a window (e.g. 10:00-12:00) in the tool call.
- For "Range" times (e.g. "between 3 and 5"), define a window in the tool call.
- For multiple services, calculate total duration and look for a continuous block.

"""

tools = [
    handle_non_booking_query,
    search_services,
    get_stylists_for_services,
    check_availability_smart,
    preview_booking_details,      # Added
    create_booking,
    get_customer_bookings,
    cancel_booking_action,
    reschedule_booking_action
]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0,
                 api_key=OPENAI_API_KEY).bind_tools(tools)


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]


async def call_model(state: GraphState):
    messages = state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

# --- Logging Setup ---


def setup_session_logger(session_id: str):
    logger = logging.getLogger(f"session.{session_id}")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []

    if not os.path.exists("logs"):
        os.makedirs("logs")

    file_handler = logging.FileHandler(f"logs/{session_id}.log", mode='w')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# --- API Interface ---


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    logger = setup_session_logger(req.session_id)

    logger.info(f"USER INPUT: {req.message}")

    # 1. RETRIEVE HISTORY
    # Get the previous messages from our global memory store for this session
    history = session_memory.get(req.session_id, [])

    # 2. PREPARE INPUT
    # We construct the input messages: System Prompt + History + New User Message

    inputs = {
        "messages": [
            ("system", SYSTEM_PROMPT),
            *history,
            HumanMessage(content=req.message)
        ]
    }

    # 3. INITIALIZE GRAPH (Safe to re-compile for this simple test context)
    workflow = StateGraph(GraphState)

    async def tool_node(state: GraphState):
        messages = state["messages"]
        last_message = messages[-1]

        tool_outputs = []

        for tool_call in last_message.tool_calls:
            logger.info(f"--- TOOL CALL ---")
            logger.info(f"Tool: {tool_call['name']}")
            logger.info(f"Input Args: {tool_call['args']}")

            selected_tool = None
            for t in tools:
                if t.name == tool_call['name']:
                    selected_tool = t
                    break

            if selected_tool:
                try:
                    output = await selected_tool.ainvoke(tool_call['args'])
                    logger.info(f"Tool Output: {output}")
                    tool_outputs.append(
                        ToolMessage(content=str(output),
                                    tool_call_id=tool_call['id'])
                    )
                except Exception as e:
                    logger.error(f"Tool Error: {e}")
                    tool_outputs.append(
                        ToolMessage(
                            content=f"Error executing tool: {e}", tool_call_id=tool_call['id'])
                    )

        return {"messages": tool_outputs}

    def should_continue(state: GraphState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return END

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    app_graph = workflow.compile()

    # 4. RUN GRAPH
    try:
        result = await app_graph.ainvoke(inputs)

        final_message = result["messages"][-1]
        logger.info(f"ASSISTANT OUTPUT: {final_message.content}")

        # 5. UPDATE MEMORY
        # The result contains the FULL conversation (System + History + New messages).
        # We slice [1:] to remove the System Prompt before saving,
        # because we re-inject the system prompt on the next request anyway.
        session_memory[req.session_id] = result["messages"][1:]

        return ChatResponse(response=final_message.content)

    except Exception as e:
        logger.error(f"Graph Execution Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
