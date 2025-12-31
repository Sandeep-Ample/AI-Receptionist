"""
Hospital Agent - Medical Office Receptionist

Example industry-specific agent for healthcare settings.
Demonstrates how to extend BaseReceptionist with custom tools.
"""

"""
Hospital Agent - Medical Office Receptionist
"""

import json
import logging
from datetime import datetime
from typing_extensions import Annotated

from livekit.agents import RunContext, function_tool

from agents.base import BaseReceptionist
from agents.registry import register_agent
from prompts.templates import VOICE_FIRST_RULES
from tools.specialty_utils import detect_specialty_from_symptoms

logger = logging.getLogger("hospital-agent")


@register_agent("hospital")
@register_agent("medical")
@register_agent("clinic")
@register_agent("default")
class HospitalAgent(BaseReceptionist):

    # ---------------------------------------------------------
    # SYSTEM PROMPT
    # ---------------------------------------------------------
    SYSTEM_PROMPT = f"""
You are a friendly and professional medical office receptionist at City Health Clinic.

Your responsibilities:
- Help patients with appointment scheduling and inquiries
- Process prescription refill requests
- Answer general questions about the clinic
- Be empathetic and supportive
- NEVER provide medical advice

{VOICE_FIRST_RULES}
"""

    GREETING_TEMPLATE = (
        "Thank you for calling City Health Clinic. How may I help you today?"
    )

    RETURNING_GREETING_TEMPLATE = (
        "Hi {name}, welcome back to City Health Clinic! How can I assist you today?"
    )

    # ---------------------------------------------------------
    # CHECK APPOINTMENT
    # ---------------------------------------------------------
    @function_tool()
    async def check_appointment(
        self,
        ctx: RunContext,
        mobile_number: Annotated[str, "Mobile number used to book the appointment"],
    ) -> str:

        APPOINTMENT_DB_PATH = "agents/data/appointments.json"

        ctx.disallow_interruptions()
        ctx.session.say("One moment while I check your appointment details...")

        try:
            with open(APPOINTMENT_DB_PATH, "r", encoding="utf-8") as f:
                appointments = json.load(f)
        except FileNotFoundError:
            return "No appointment records found."

        appointment = next(
            (a for a in appointments if a.get("mobile_number") == mobile_number), None
        )

        if not appointment:
            return "No appointment found for this mobile number."

        return (
            f"Found appointment for {appointment['patient_name']}: "
            f"{appointment['doctor_name']} on "
            f"{appointment['appointment_datetime']} "
            f"for a {appointment['specialty']} consultation."
        )

    # ---------------------------------------------------------
    # SCHEDULE APPOINTMENT
    # ---------------------------------------------------------
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

        import os
        from datetime import datetime, time

        DOCTOR_JSON_PATH = "agents/data/doctors.json"
        APPOINTMENT_JSON_PATH = "agents/data/appointments.json"

        ctx.disallow_interruptions()

        # -----------------------------
        # Parse DOB
        # -----------------------------
        try:
            parsed_dob = datetime.strptime(dob, "%d-%m-%Y").strftime("%d-%m-%Y")
        except ValueError:
            return "Please provide date of birth in DD-MM-YYYY format."

        # -----------------------------
        # Parse appointment date & time
        # -----------------------------
        try:
            parsed_dt = datetime.strptime(preferred_date, "%d-%m-%Y %H:%M")
        except ValueError:
            return (
                "Please provide appointment date and time in this format: "
                "DD-MM-YYYY HH:MM (example: 25-01-2025 14:30)"
            )

        preferred_time = parsed_dt.time()
        preferred_date_str = parsed_dt.strftime("%d-%m-%Y %H:%M")

        # -----------------------------
        # Detect specialty
        # -----------------------------
        specialty = detect_specialty_from_symptoms(reason)
        if not specialty:
            return "Please describe your symptoms again."

        specialty_key = specialty.lower().strip()

        # -----------------------------
        # Load doctors
        # -----------------------------
        try:
            with open(DOCTOR_JSON_PATH, "r", encoding="utf-8") as f:
                doctors = json.load(f).get("doctors", [])
        except FileNotFoundError:
            return "Doctor database not found."

        matching_doctors = [
            d
            for d in doctors
            if d.get("status", "").lower() == "available"
            and d.get("specialty", "").lower().strip() == specialty_key
        ]

        if not matching_doctors:
            return f"No {specialty} doctor is available at the moment."

        # -----------------------------
        # Match time shift
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
                f"{specialty} doctors are not available at "
                f"{preferred_time.strftime('%I:%M %p')}."
            )

        # -----------------------------
        # Ensure appointment file exists
        # -----------------------------
        os.makedirs(os.path.dirname(APPOINTMENT_JSON_PATH), exist_ok=True)

        if not os.path.exists(APPOINTMENT_JSON_PATH):
            with open(APPOINTMENT_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)

        with open(APPOINTMENT_JSON_PATH, "r", encoding="utf-8") as f:
            appointments = json.load(f)

        appointments.append(
            {
                "appointment_id": f"APT-{int(datetime.now().timestamp())}",
                "patient_name": patient_name,
                "mobile_number": mobile_number,
                "dob": parsed_dob,
                "gender": gender,
                "reason": reason,
                "specialty": specialty,
                "doctor_name": selected_doctor["name"],
                "appointment_datetime": preferred_date_str,
                "created_at": datetime.now().isoformat(),
            }
        )

        with open(APPOINTMENT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(appointments, f, indent=4)

        return (
            f"✅ Appointment scheduled successfully!\n\n"
            f"Patient: {patient_name}\n"
            f"Doctor: {selected_doctor['name']}\n"
            f"Specialty: {specialty}\n"
            f"Date & Time: {preferred_date_str}"
        )

    # ---------------------------------------------------------
    # RESCHEDULE APPOINTMENT
    # ---------------------------------------------------------
    @function_tool()
    async def reschedule_appointment(
        self,
        ctx: RunContext,
        mobile_number: Annotated[str, "Mobile number used to book"],
        new_preferred_date: Annotated[str, "New date (DD-MM-YYYY HH:MM)"],
    ) -> str:

        APPOINTMENT_DB_PATH = "agents/data/appointments.json"

        with open(APPOINTMENT_DB_PATH, "r", encoding="utf-8") as f:
            appointments = json.load(f)

        appointment = next(
            (a for a in appointments if a["mobile_number"] == mobile_number), None
        )

        if not appointment:
            return "Appointment not found."

        appointment["appointment_datetime"] = new_preferred_date

        with open(APPOINTMENT_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(appointments, f, indent=4)

        return (
            f"✅ Appointment rescheduled for {appointment['patient_name']} "
            f"on {new_preferred_date}."
        )

    # ---------------------------------------------------------
    # OTHER TOOLS
    # ---------------------------------------------------------
    @function_tool()
    async def request_prescription_refill(
        self,
        ctx: RunContext,
        patient_name: Annotated[str, "Patient name"],
        medication_name: Annotated[str, "Medication name"],
    ) -> str:
        return f"Refill request submitted for {medication_name}."

    @function_tool()
    async def get_clinic_hours(self, ctx: RunContext) -> str:
        return "Clinic hours are Monday–Friday, 8 AM to 6 PM."

    @function_tool()
    async def get_clinic_location(self, ctx: RunContext) -> str:
        return "123 Health Avenue, Medical Plaza."
