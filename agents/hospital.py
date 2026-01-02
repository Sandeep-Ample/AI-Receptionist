"""
Hospital Agent - Medical Office Receptionist

Example industry-specific agent for healthcare settings.
Demonstrates how to extend BaseReceptionist with custom tools.
"""

import asyncio
import logging
from typing import Annotated, Optional

from dateutil import parser
from livekit.agents import RunContext, function_tool

from agents.base import BaseReceptionist
from agents.registry import register_agent
from memory.service import get_memory_service
from prompts.templates import VOICE_FIRST_RULES

logger = logging.getLogger("hospital-agent")
from tools.session_logger import log_tool_call


@register_agent("hospital")
@register_agent("medical")
@register_agent("clinic")
@register_agent("default")  # Hospital is the default agent
class HospitalAgent(BaseReceptionist):
    """
    Medical office receptionist for clinics and hospitals.
    
    Handles:
    - Appointment scheduling and inquiries
    - Prescription refill requests
    - General medical office questions
    - HIPAA-conscious communication
    """
    
    SYSTEM_PROMPT = f"""You are a friendly and professional medical office receptionist at City Health Clinic.

Your responsibilities:
- Help patients with appointment scheduling and inquiries
- Process prescription refill requests
- Answer general questions about the clinic
- Be empathetic and supportive, especially with worried patients
- NEVER provide medical advice - always direct medical questions to healthcare providers

Important guidelines:
- Be HIPAA-conscious - never share patient information openly
- If a patient seems distressed, acknowledge their feelings first
- For emergencies, instruct them to call 911 or go to the ER immediately

{VOICE_FIRST_RULES}"""

    GREETING_TEMPLATE = "Thank you for calling City Health Clinic. How may I help you today?"
    RETURNING_GREETING_TEMPLATE = "Hi {name}, welcome back to City Health Clinic! How can I assist you today?"
    
    @function_tool()
    @log_tool_call
    async def check_appointment(
        self,
        ctx: RunContext,
        patient_name: Annotated[str, "The patient's full name"]
    ) -> str:
        """
        Look up a patient's upcoming appointments.
        Use this when a patient asks about their scheduled appointments.
        """
        logger.info(f"Checking appointments for: {patient_name}")
        pool = get_memory_service()._pool
        
        # Protect from interruptions during lookup
        ctx.disallow_interruptions()
        # Verbal filler while "looking up"
        ctx.session.say("One moment while I check your appointments...")

        row = await pool.fetchrow(
        "SELECT a.appointment_time, d.name FROM hospital_appointments a "
        "JOIN hospital_doctors d ON a.doctor_id = d.id "
        "WHERE a.patient_identity = $1", ctx.participant.identity
    )
        
        if row:
            return f"I found your appointment with {row['name']} at {row['appointment_time']}."
        return "I couldn't find any appointments scheduled for you."    
    @function_tool()
    @log_tool_call
    async def schedule_appointment(
        self,
        ctx: RunContext,
        patient_name: Annotated[str, "The patient's full name"],
        doctor_name: Annotated[str, "The name of the doctor"],
        preferred_date: Annotated[str, "Preferred date and time for the appointment"],
        reason: Annotated[str, "Reason for the visit"]
    ) -> str:
        """
        Schedule a new appointment for a patient.
        Collect the patient's name, preferred date, and reason for visit.
        """
        logger.info(f"Scheduling appointment: {patient_name}, {preferred_date}, {reason}")
        
        ctx.disallow_interruptions()
        ctx.session.say("Let me check our availability for that date...")
        
        pool = get_memory_service()._pool
        # 2. Get the Doctor ID
        # We use ILIKE so 'dr smith' matches 'Dr. Smith'
        query = "SELECT id FROM hospital_doctors WHERE name ILIKE $1"
        doctor_row = await pool.fetchrow(query, f"%{doctor_name}%")
        if not doctor_row:
            return f"I'm sorry, I couldn't find a doctor named {doctor_name} in our system."
        doctor_id = doctor_row['id']

        # 1. Parse the string date from the AI into a real date object
        # (You might need 'dateutil.parser' for this)
        appt_dt = parser.parse(preferred_date)
        day_of_week = appt_dt.weekday() # 0-6
        appt_time = appt_dt.time()

        # 2. Check availability table
        avail_query = """
            SELECT start_time, end_time 
            FROM doctor_availability 
            WHERE doctor_id = $1 AND day_of_week = $2
        """
        availability = await pool.fetchrow(avail_query, doctor_id, day_of_week)


        if not availability:
            return f"I'm sorry, that doctor does not work on that day of the week."
        # 3. Check if the time is within their shift
        if not (availability['start_time'] <= appt_time <= availability['end_time']):
            return f"That doctor is only available between {availability['start_time']} and {availability['end_time']}."

        conflict_query = """
            SELECT id FROM hospital_appointments 
            WHERE doctor_id = $1 AND appointment_time = $2 AND status = 'scheduled'
        """
        conflict = await pool.fetchrow(conflict_query, doctor_id, appt_dt)

        if conflict:
            return "I'm sorry, that specific time slot is already booked by another patient."


        insert_query = """
            INSERT INTO hospital_appointments (patient_identity, doctor_id, appointment_time, reason)
            VALUES ($1, $2, $3, $4)
        """
        await pool.execute(insert_query, ctx.participant.identity, doctor_id, appt_dt, reason)

        return f"Perfect! I've scheduled your appointment for {preferred_date}. See you then!"


    @function_tool()
    @log_tool_call
    async def lookup_doctors(
        self,
        ctx: RunContext,
        specialty: Annotated[Optional[str], "Optional specialty to filter by (e.g., 'Pediatrics')"] = None
    ) -> str:
        """
        Get a list of doctors and their specialties.
        Use this when a patient asks who works here or wants a recommendation.
        """
        logger.info(f"Looking up doctors - specialty filter: {specialty}")
        pool = get_memory_service()._pool
        
        if specialty:
            query = "SELECT name, specialty FROM hospital_doctors WHERE specialty ILIKE $1"
            rows = await pool.fetch(query, f"%{specialty}%")
        else:
            query = "SELECT name, specialty FROM hospital_doctors"
            rows = await pool.fetch(query)
            
        if not rows:
            return "I'm sorry, I couldn't find any doctors matching that description."
            
        doctor_list = [f"{r['name']} ({r['specialty']})" for r in rows]
        return "Our available doctors include: " + ", ".join(doctor_list)

    @function_tool()
    @log_tool_call
    async def cancel_appointment(
        self,
        ctx: RunContext,
        appointment_time: Annotated[str, "The date and time of the appointment to cancel"]
    ) -> str:
        """
        Cancel an existing appointment.
        """
        logger.info(f"Cancelling appointment for: {ctx.participant.identity} at {appointment_time}")
        pool = get_memory_service()._pool
        
        ctx.disallow_interruptions()
        
        try:
            # We use the existing 'parser' import to handle the AI's date string
            appt_dt = parser.parse(appointment_time)
        except Exception:
            return "I couldn't understand that date format. Could you please specify it more clearly?"

        # Update the database
        result = await pool.execute(
            "DELETE FROM hospital_appointments WHERE patient_identity = $1 AND appointment_time = $2",
            ctx.participant.identity, appt_dt
        )
        
        if result == "DELETE 1":
            return f"I've successfully cancelled your appointment for {appointment_time}."
        return "I couldn't find an appointment at that specific time to cancel."


    @function_tool()
    @log_tool_call
    async def get_clinic_info(self, ctx: RunContext) -> str:
        """
        Get general information about City Health Clinic, including hours, 
        location, and contact details.
        """
        # This keeps the AI factually accurate and avoids hallucinations
        info = {
            "name": "City Health Clinic",
            "address": "123 Medical Plaza, Suite 400, Downtown",
            "hours": {
                "Monday-Friday": "8:00 AM - 6:00 PM",
                "Saturday": "9:00 AM - 2:00 PM",
                "Sunday": "Closed"
            },
            "parking": "Free parking is available in the deck behind the building.",
            "emergency_policy": "For life-threatening emergencies, please call 911 immediately.",
            "cancellation_policy": "Please provide at least 24 hours notice for any cancellations."
        }
        
        # Formatting for the AI's internal "reading"
        hours_str = ", ".join([f"{day} ({time})" for day, time in info['hours'].items()])
        
        return (
            f"Welcome to {info['name']}. We are located at {info['address']}. "
            f"Our hours are: {hours_str}. {info['parking']} "
            f"Note: {info['cancellation_policy']} {info['emergency_policy']}"
        )