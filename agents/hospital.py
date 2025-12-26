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

import json
import asyncio
import logging
from datetime import datetime
from typing_extensions import Annotated

from tools.specialty_utils import detect_specialty_from_symptoms


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

    GREETING_TEMPLATE = (
        "Thank you for calling City Health Clinic. How may I help you today?"
    )
    RETURNING_GREETING_TEMPLATE = (
        "Hi {name}, welcome back to City Health Clinic! How can I assist you today?"
    )

    # @function_tool()
    # async def check_appointment(
    #     self, ctx: RunContext, patient_name: Annotated[str, "The patient's full name"]
    # ) -> str:
    #     """
    #     Look up a patient's upcoming appointments.
    #     Use this when a patient asks about their scheduled appointments.
    #     """
    #     logger.info(f"Checking appointments for: {patient_name}")

    #     # Protect from interruptions during lookup
    #     ctx.disallow_interruptions()

    #     # Verbal filler while "looking up"
    #     ctx.session.say("One moment while I check your appointments...")

    #     # Simulate database lookup
    #     await asyncio.sleep(1.5)

    #     # Mock response - in production, this would query a real system
    #     return f"Found appointment for {patient_name}: Dr. Smith on Friday at 2:30 PM for a general checkup."
    
    @function_tool()
    async def check_appointment(
        self,
        ctx: RunContext,
        mobile_number: Annotated[str, "Mobile number used to book the appointment"]
    ) -> str:
        """
        Check an existing appointment using the patient's mobile number.
        """

        APPOINTMENT_DB_PATH = "data/appointments.json"

        logger.info(f"Checking appointment for mobile: {mobile_number}")

        ctx.disallow_interruptions()
        ctx.session.say("One moment while I check your appointment details...")

        # -----------------------------
        # Load appointments
        # -----------------------------
        try:
            with open(APPOINTMENT_DB_PATH, "r", encoding="utf-8") as f:
                appointments = json.load(f)
        except FileNotFoundError:
            return (
                "I could not find any appointment records at the moment. "
                "Please contact the clinic for assistance."
            )

        appointment = next(
            (a for a in appointments if a.get("mobile_number") == mobile_number),
            None
        )

        if not appointment:
            return (
                "Sorry, I could not find any appointment associated with this "
                "mobile number. Please check the number and try again."
            )

        # -----------------------------
        # Extract details
        # -----------------------------
        patient_name = appointment["patient_name"]
        doctor_name = appointment["doctor_name"]
        date_time = appointment["date_time"]
        specialty = appointment["specialty"]

        # -----------------------------
        # REQUIRED RETURN FORMAT
        # -----------------------------
        return (
            f"Found appointment for {patient_name}: "
            f"{doctor_name} on {date_time} for a {specialty} consultation."
        )
    
    

    # @function_tool()
    # async def schedule_appointment(
    #     self,
    #     ctx: RunContext,
    #     patient_name: Annotated[str, "The patient's full name"],
    #     preferred_date: Annotated[str, "Preferred date for the appointment"],
    #     reason: Annotated[str, "Reason for the visit"]
    # ) -> str:
    #     """
    #     Schedule a new appointment for a patient.
    #     Collect the patient's name, preferred date, and reason for visit.
    #     """
    #     logger.info(f"Scheduling appointment: {patient_name}, {preferred_date}, {reason}")

    #     ctx.disallow_interruptions()
    #     ctx.session.say("Let me check our availability for that date...")

    #     await asyncio.sleep(2.0)

    #     # Mock response
    #     return f"Appointment scheduled for {patient_name} on {preferred_date} for {reason}. The patient will receive a confirmation text."

    @function_tool()
    async def schedule_appointment(
        self,
        ctx: RunContext,
        patient_name: Annotated[str, "The patient's full name"],
        mobile_number: Annotated[str, "Patient's mobile phone number"],
        dob: Annotated[str, "Patient's date of birth (DD-MM-YYYY)"],
        gender: Annotated[str, "Patient's gender"],
        preferred_date: Annotated[str, "Preferred date and time (DD-MM-YYYY HH:MM)"],
        reason: Annotated[str, "Reason for the visit / symptoms"],
    ) -> str:
        """
        Schedule a new appointment after validating doctor availability.
        """

        DOCTOR_JSON_PATH = "data/doctors.json"

        logger.info(
            f"Scheduling appointment: {patient_name}, {mobile_number}, "
            f"{dob}, {gender}, {preferred_date}, {reason}"
        )

        ctx.disallow_interruptions()

    # -----------------------------
    # Detect specialty (SAFE)
    # -----------------------------
        specialty = detect_specialty_from_symptoms(reason)

        if specialty is None:
           return (
            "Please tell me the symptoms or reason for your visit "
            "so I can help you choose the right doctor."
        )

    # -----------------------------
    # Load doctors
    # -----------------------------
        with open(DOCTOR_JSON_PATH, "r", encoding="utf-8") as f:
            doctors = json.load(f).get("doctors", [])

        matching_doctors = [
            d for d in doctors if d.get("specialty", "").lower() == specialty.lower()
        ]

        if not matching_doctors:
            return f"Sorry, no doctors are available for {specialty} at the moment."

    # -----------------------------
    # Parse preferred date & time
    # -----------------------------
        try:
            preferred_dt = datetime.strptime(preferred_date, "%d-%m-%Y %H:%M")
            preferred_time = preferred_dt.time()
        except ValueError:
            return "Please provide the date and time in DD-MM-YYYY HH:MM format."

    # -----------------------------
    # Check doctor availability
    # -----------------------------
        selected_doctor = None

        for doctor in matching_doctors:
            start_str, end_str = doctor["time_shift"].split("-")
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()

            if start_time <= preferred_time <= end_time:
               selected_doctor = doctor
               break

        if not selected_doctor:
           return (
              f"Doctors from {specialty} are not available at that time. "
              "Please choose another date or time."
           )

    # -----------------------------
    # Confirm booking
    # -----------------------------
        ctx.session.say("Checking availability and confirming your appointment...")
        await asyncio.sleep(2.0)

        return (
            f"✅ Appointment successfully scheduled!\n\n"
            f"Patient: {patient_name}\n"
            f"Doctor: {selected_doctor['name']}\n"
            f"Specialty: {specialty}\n"
            f"Date & Time: {preferred_date}\n\n"
            f"A confirmation message will be sent to {mobile_number}."
        )
        
    @function_tool()
    async def reschedule_appointment(
        self,
        ctx: RunContext,
        mobile_number: Annotated[str, "Mobile number used to book the appointment"],
        new_preferred_date: Annotated[str, "New preferred date and time (DD-MM-YYYY HH:MM)"],
    ) -> str:
        """
        Reschedule an existing appointment after validating availability.
        """

        APPOINTMENT_DB_PATH = "data/appointments.json"
        DOCTOR_JSON_PATH = "data/doctors.json"

        logger.info(
            f"Reschedule request for mobile: {mobile_number}, "
            f"new date: {new_preferred_date}"
        )

        ctx.disallow_interruptions()

        # -----------------------------
        # Load appointments (MOCK DB)
        # -----------------------------
        try:
            with open(APPOINTMENT_DB_PATH, "r", encoding="utf-8") as f:
                appointments = json.load(f)
        except FileNotFoundError:
            return (
                "I could not find any appointment records. "
                "Please contact the clinic for assistance."
            )

        appointment = next(
            (a for a in appointments if a.get("mobile_number") == mobile_number),
            None
        )

        if not appointment:
            return (
                "Sorry, I could not find any appointment associated with this "
                "mobile number. Please check and try again."
            )

        # -----------------------------
        # Show existing appointment
        # -----------------------------
        patient_name = appointment["patient_name"]
        doctor_name = appointment["doctor_name"]
        specialty = appointment["specialty"]
        current_datetime = appointment["date_time"]

        ctx.session.say(
            f"I found your appointment. Patient name is {patient_name}, "
            f"doctor is {doctor_name}, currently scheduled on {current_datetime}."
        )

        # -----------------------------
        # Parse new preferred date & time
        # -----------------------------
        try:
            new_dt = datetime.strptime(new_preferred_date, "%d-%m-%Y %H:%M")
            new_time = new_dt.time()
        except ValueError:
            return "Please provide the date and time in DD-MM-YYYY HH:MM format."

        # -----------------------------
        # Load doctors
        # -----------------------------
        with open(DOCTOR_JSON_PATH, "r", encoding="utf-8") as f:
            doctors = json.load(f).get("doctors", [])

        doctor = next(
            (d for d in doctors if d.get("name") == doctor_name),
            None
        )

        if not doctor:
            return (
                "The doctor for this appointment could not be found. "
                "Please contact the clinic for assistance."
            )

        # -----------------------------
        # Check doctor availability
        # -----------------------------
        start_str, end_str = doctor["time_shift"].split("-")
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()

        if not (start_time <= new_time <= end_time):
            return (
                f"The doctor is not available at that time. "
                "Please choose another preferred date and time."
            )

        # -----------------------------
        # Save updated appointment (MOCK SAVE)
        # -----------------------------
        appointment["date_time"] = new_preferred_date

        with open(APPOINTMENT_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(appointments, f, indent=2)

        # -----------------------------
        # Confirm reschedule
        # -----------------------------
        ctx.session.say("Updating your appointment. Please wait...")
        await asyncio.sleep(2.0)

        return (
            f"✅ Your appointment has been successfully rescheduled.\n\n"
            f"Patient: {patient_name}\n"
            f"Doctor: {doctor_name}\n"
            f"Specialty: {specialty}\n"
            f"New Date & Time: {new_preferred_date}\n\n"
            "You will receive a confirmation message shortly."
        )


    @function_tool()
    async def request_prescription_refill(
        self,
        ctx: RunContext,
        patient_name: Annotated[str, "The patient's full name"],
        medication_name: Annotated[str, "Name of the medication to refill"],
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
