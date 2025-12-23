"""
Hospital Agent - Medical Office Receptionist

Example industry-specific agent for healthcare settings.
Demonstrates how to extend BaseReceptionist with custom tools.
"""

import asyncio
import logging
from typing import Annotated

from livekit.agents import RunContext, function_tool

from agents.base import BaseReceptionist
from agents.registry import register_agent
from prompts.templates import VOICE_FIRST_RULES

logger = logging.getLogger("hospital-agent")


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
        
        # Protect from interruptions during lookup
        ctx.disallow_interruptions()
        
        # Verbal filler while "looking up"
        ctx.session.say("One moment while I check your appointments...")
        
        # Simulate database lookup
        await asyncio.sleep(1.5)
        
        # Mock response - in production, this would query a real system
        return f"Found appointment for {patient_name}: Dr. Smith on Friday at 2:30 PM for a general checkup."

    @function_tool()
    async def schedule_appointment(
        self,
        ctx: RunContext,
        patient_name: Annotated[str, "The patient's full name"],
        preferred_date: Annotated[str, "Preferred date for the appointment"],
        reason: Annotated[str, "Reason for the visit"]
    ) -> str:
        """
        Schedule a new appointment for a patient.
        Collect the patient's name, preferred date, and reason for visit.
        """
        logger.info(f"Scheduling appointment: {patient_name}, {preferred_date}, {reason}")
        
        ctx.disallow_interruptions()
        ctx.session.say("Let me check our availability for that date...")
        
        await asyncio.sleep(2.0)
        
        # Mock response
        return f"Appointment scheduled for {patient_name} on {preferred_date} for {reason}. The patient will receive a confirmation text."

    @function_tool()
    async def request_prescription_refill(
        self,
        ctx: RunContext,
        patient_name: Annotated[str, "The patient's full name"],
        medication_name: Annotated[str, "Name of the medication to refill"]
    ) -> str:
        """
        Submit a prescription refill request.
        The pharmacy will be notified once the doctor approves.
        """
        logger.info(f"Refill request: {patient_name}, {medication_name}")
        
        ctx.disallow_interruptions()
        ctx.session.say("I'm submitting that refill request now...")
        
        await asyncio.sleep(1.5)
        
        return f"Refill request submitted for {medication_name}. The doctor will review it within 24-48 hours, and the pharmacy will be notified once approved."

    @function_tool()
    async def get_clinic_hours(self, ctx: RunContext) -> str:
        """
        Provide the clinic's operating hours.
        Use this when patients ask about when the clinic is open.
        """
        return "City Health Clinic is open Monday through Friday, 8 AM to 6 PM, and Saturday 9 AM to 1 PM. We're closed on Sundays."

    @function_tool()
    async def get_clinic_location(self, ctx: RunContext) -> str:
        """
        Provide the clinic's address and directions.
        Use this when patients ask where the clinic is located.
        """
        return "We're located at 123 Health Avenue, Suite 200, in the Medical Plaza building. Free parking is available in the adjacent garage."
