"""
Salon Agent - Beauty Salon Receptionist

Handles:
- Service inquiries (search, pricing, duration)
- Stylist search and availability
- Appointment booking, cancellation, rescheduling
- General inquiries (hours, location)
"""

import logging
from typing import Annotated, Optional, List
from datetime import datetime, timedelta, time, date

from dateutil import parser
from livekit.agents import RunContext, function_tool

from agents.base import BaseReceptionist
from agents.registry import register_agent
from memory.salon_service import get_salon_service
from tools.session_logger import log_tool_call

logger = logging.getLogger("salon-agent")


@register_agent("salon")
@register_agent("beauty")
@register_agent("spa")
class SalonAgent(BaseReceptionist):
    """
    Beauty salon receptionist backed by a live database.
    
    Handles bookings, service inquiries, and stylist availability.
    """
    
    SYSTEM_PROMPT_TEMPLATE = """You are a professional receptionist for Luxe Salon & Spa, connected to a live database.

TODAY'S DATE: {current_date} ({current_day})

CRITICAL CONSTRAINTS:
1. NO HALLUCINATIONS: You have ZERO knowledge of services, stylists, or availability outside of tools.
   - If user asks about services, call `search_services`.
   - If user asks about stylists for a service, call `get_stylists_for_service`.
   - To check availability, use `check_stylist_availability`.
   - Never guess a stylist's name or available times.

2. BOOKING WORKFLOW:
   Step 1: Service Selection - Ask which service they want, use `search_services` to confirm it exists.
   Step 2: Stylist Selection - Use `get_stylists_for_service` to find who can perform it. Ask user to choose.
   Step 3: Date & Time - Ask when they'd like to come. Parse natural language dates like "tomorrow" or "next Monday".
   Step 4: Availability Check - Call `check_stylist_availability` to verify the slot is open.
   Step 5: Customer Details - Ask for their name and phone number (10 digits).
   Step 6: Confirmation - Summarize the booking and ask for confirmation.
   Step 7: Book - Call `book_appointment` only after explicit "yes" confirmation.

3. CANCELLATION WORKFLOW:
   - Ask for phone number → Call `find_customer_bookings` → Show bookings → Ask which to cancel → Call `cancel_booking`.

4. RESCHEDULING WORKFLOW:
   - Ask for phone number → Call `find_customer_bookings` → Ask which to reschedule.
   - Get new date/time → Check availability → Call `reschedule_booking`.

5. GENERAL RULES:
   - Phone numbers must be exactly 10 digits.
   - Always confirm before making any booking or cancellation.
   - Be warm, friendly, and professional.
   - Keep responses concise for voice - avoid long lists.

6. DATE/TIME HANDLING:
   - Accept natural language: "tomorrow", "next Monday", "January 25th"
   - Accept times: "2 PM", "14:00", "2:30 in the afternoon"
   - If unclear, ask for clarification.
"""

    @property
    def SYSTEM_PROMPT(self) -> str:
        """Generate system prompt with current date."""
        now = datetime.now()
        return self.SYSTEM_PROMPT_TEMPLATE.format(
            current_date=now.strftime("%B %d, %Y"),
            current_day=now.strftime("%A")
        )

    GREETING_TEMPLATE = "Thank you for calling Luxe Salon and Spa. How can I help you today?"
    RETURNING_GREETING_TEMPLATE = "Hi {name}, welcome back to Luxe Salon and Spa! How can I help you today?"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = get_salon_service()

    # --- 1. Service Search ---

    @function_tool()
    @log_tool_call
    async def search_services(
        self,
        ctx: RunContext,
        search_term: Annotated[Optional[str], "Service name or keyword to search for (e.g. 'haircut', 'facial')"] = None
    ) -> str:
        """
        Search for available salon services.
        If no search term provided, lists all services.
        """
        logger.info(f"Searching services: {search_term}")
        
        services = await self.db.get_services(search_term)
        
        if not services:
            if search_term:
                return f"I couldn't find any services matching '{search_term}'. Would you like me to list all our services?"
            return "I'm having trouble accessing our service list right now."
        
        # Format for voice - keep it concise
        if len(services) == 1:
            s = services[0]
            return f"We offer {s['name']} for ${s['price']}, which takes about {s['duration_minutes']} minutes. Would you like to book this?"
        
        # Multiple services - summarize for voice
        if len(services) <= 4:
            service_list = [f"{s['name']} at ${s['price']}" for s in services]
            return f"We have: {', '.join(service_list)}. Which one interests you?"
        else:
            # Too many to read - give highlights
            return f"We have {len(services)} services available. Some popular ones are {services[0]['name']}, {services[1]['name']}, and {services[2]['name']}. What type of service are you looking for?"

    # --- 2. Stylist Search ---

    @function_tool()
    @log_tool_call
    async def get_stylists_for_service(
        self,
        ctx: RunContext,
        service_name: Annotated[str, "The service name to find stylists for"]
    ) -> str:
        """
        Find stylists who can perform a specific service.
        """
        logger.info(f"Finding stylists for service: {service_name}")
        
        stylists = await self.db.get_stylists_for_service(service_name)
        
        if not stylists:
            return f"I couldn't find any stylists who offer {service_name}. Would you like to try a different service?"
        
        # Deduplicate stylist names
        unique_stylists = list(set(s['stylist_name'] for s in stylists))
        
        if len(unique_stylists) == 1:
            return f"For {service_name}, we have {unique_stylists[0]} available. Would you like to book with them?"
        else:
            return f"For {service_name}, we have {', '.join(unique_stylists)}. Who would you prefer?"

    # --- 3. Availability Check ---

    @function_tool()
    @log_tool_call
    async def check_stylist_availability(
        self,
        ctx: RunContext,
        stylist_name: Annotated[str, "Name of the stylist"],
        date_str: Annotated[str, "Desired date (e.g. 'tomorrow', 'next Monday', 'January 25')"],
        time_str: Annotated[str, "Desired time (e.g. '2 PM', '14:00')"],
        duration_minutes: Annotated[int, "Duration of the service in minutes"] = 30
    ) -> str:
        """
        Check if a stylist is available at a specific date and time.
        """
        logger.info(f"Checking availability: {stylist_name} on {date_str} at {time_str}")
        ctx.disallow_interruptions()
        
        # 1. Parse date
        try:
            parsed_date = parser.parse(date_str, fuzzy=True, default=datetime.now())
            if parsed_date.date() < datetime.now().date():
                return "I cannot check availability in the past. Please choose a future date."
            booking_date = parsed_date.date()
        except:
            return "I didn't catch the date. Could you say 'tomorrow', 'next Monday', or a specific date like 'January 25th'?"
        
        # 2. Parse time
        try:
            parsed_time = parser.parse(time_str, default=datetime.now()).time()
        except:
            return "I couldn't understand the time. Could you say it like '2 PM' or '14:00'?"
        
        # 3. Get stylist
        stylist = await self.db.get_stylist_details(stylist_name)
        if not stylist:
            return f"I couldn't find a stylist named {stylist_name}."
        
        stylist_id = stylist['stylist_id']
        day_name = booking_date.strftime("%A").lower()
        
        # 4. Check salon hours
        salon_hours = await self.db.get_salon_hours(day_name)
        if not salon_hours:
            return f"Sorry, the salon is closed on {day_name.title()}s."
        
        if salon_hours.get('is_closed'):
            return f"Sorry, the salon is closed on {day_name.title()}s."
        
        open_time = salon_hours['open_time']
        close_time = salon_hours['close_time']
        
        if not (open_time <= parsed_time < close_time):
            return f"The salon is open from {open_time.strftime('%I:%M %p')} to {close_time.strftime('%I:%M %p')}. Please choose a time within these hours."
        
        # 5. Check stylist availability for the date
        stylist_shift = await self.db.get_stylist_availability(stylist_id, booking_date)
        if not stylist_shift:
            return f"{stylist['name']} is not scheduled to work on {booking_date.strftime('%A, %B %d')}. Would you like to try another date or stylist?"
        
        shift_start = stylist_shift['start_time']
        shift_end = stylist_shift['end_time']
        
        if not (shift_start <= parsed_time):
            return f"{stylist['name']} starts at {shift_start.strftime('%I:%M %p')} on that day. Would you like that time instead?"
        
        # Calculate end time
        end_dt = datetime.combine(booking_date, parsed_time) + timedelta(minutes=duration_minutes)
        end_time = end_dt.time()
        
        if end_time > shift_end:
            return f"{stylist['name']}'s shift ends at {shift_end.strftime('%I:%M %p')}. The appointment wouldn't fit. Please choose an earlier time."
        
        # 6. Check for conflicting bookings
        is_available = await self.db.check_slot_available(stylist_id, booking_date, parsed_time, end_time)
        
        if not is_available:
            return f"Sorry, {stylist['name']} is already booked at {parsed_time.strftime('%I:%M %p')}. Would you like to try a different time?"
        
        # Slot is available!
        return f"Great news! {stylist['name']} is available on {booking_date.strftime('%A, %B %d')} at {parsed_time.strftime('%I:%M %p')}. Shall I book this for you?"

    # --- 4. Booking ---

    @function_tool()
    @log_tool_call
    async def book_appointment(
        self,
        ctx: RunContext,
        stylist_name: Annotated[str, "Name of the stylist"],
        service_name: Annotated[str, "Name of the service"],
        date_str: Annotated[str, "Date of appointment"],
        time_str: Annotated[str, "Time of appointment"],
        customer_name: Annotated[str, "Customer's full name"],
        customer_phone: Annotated[str, "Customer's 10-digit phone number"],
        notes: Annotated[Optional[str], "Any special requests or notes"] = None
    ) -> str:
        """
        Book an appointment. Call only after user confirms.
        """
        logger.info(f"Booking: {customer_name} with {stylist_name} for {service_name}")
        ctx.disallow_interruptions()
        
        # Validate phone number
        phone_digits = ''.join(filter(str.isdigit, customer_phone))
        if len(phone_digits) != 10:
            return "The phone number must be exactly 10 digits. Could you please provide it again?"
        
        # 1. Parse date/time
        try:
            p_date = parser.parse(date_str, fuzzy=True, default=datetime.now()).date()
            p_time = parser.parse(time_str, default=datetime.now()).time()
        except:
            return "I'm having trouble with the date or time format. Could you repeat it?"
        
        # 2. Get stylist
        stylist = await self.db.get_stylist_details(stylist_name)
        if not stylist:
            return f"Stylist {stylist_name} not found."
        
        # 3. Get service
        service = await self.db.get_service_details(service_name)
        if not service:
            return f"Service {service_name} not found."
        
        # 4. Calculate end time
        duration = service['duration_minutes']
        end_dt = datetime.combine(p_date, p_time) + timedelta(minutes=duration)
        end_time = end_dt.time()
        
        # 5. Final availability check
        is_available = await self.db.check_slot_available(stylist['stylist_id'], p_date, p_time, end_time)
        if not is_available:
            return "Oh no! That slot was just booked by someone else. Would you like to try a different time?"
        
        # 6. Create/get customer
        try:
            customer_id = await self.db.ensure_customer(customer_name, phone_digits)
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            return "I had trouble saving your information. Please try again."
        
        # 7. Create booking
        try:
            booking_id = await self.db.create_booking(
                customer_id=customer_id,
                stylist_id=stylist['stylist_id'],
                service_id=service['service_id'],
                booking_date=p_date,
                start_time=p_time,
                end_time=end_time,
                notes=notes
            )
            
            if not booking_id:
                return "I apologize, there was a problem creating the booking. Please try again."
            
            arrival_time = (datetime.combine(p_date, p_time) - timedelta(minutes=10)).strftime("%I:%M %p")
            return f"Your appointment is confirmed! You're booked with {stylist['name']} for {service['name']} on {p_date.strftime('%A, %B %d')} at {p_time.strftime('%I:%M %p')}. Please arrive by {arrival_time}. See you then!"
            
        except Exception as e:
            logger.error(f"Booking error: {e}")
            return "I apologize, something went wrong while saving your appointment."

    # --- 5. Find Bookings ---

    @function_tool()
    @log_tool_call
    async def find_customer_bookings(
        self,
        ctx: RunContext,
        phone_number: Annotated[str, "Customer's 10-digit phone number"]
    ) -> str:
        """
        Find upcoming bookings for a customer by phone number.
        """
        phone_digits = ''.join(filter(str.isdigit, phone_number))
        if len(phone_digits) != 10:
            return "Please provide a valid 10-digit phone number."
        
        logger.info(f"Finding bookings for phone: {phone_digits}")
        
        bookings = await self.db.find_customer_bookings(phone_digits)
        
        if not bookings:
            return f"I couldn't find any upcoming appointments for that phone number. Would you like to book a new appointment?"
        
        # Format for voice
        response = f"I found {len(bookings)} upcoming appointment{'s' if len(bookings) > 1 else ''}. "
        
        for i, b in enumerate(bookings, 1):
            date_str = b['booking_date'].strftime("%A, %B %d")
            time_str = b['start_time'].strftime("%I:%M %p")
            response += f"Number {i}: {b['service_name']} with {b['stylist_name']} on {date_str} at {time_str}. "
        
        response += "Which one would you like to modify?"
        return response

    # --- 6. Cancel Booking ---

    @function_tool()
    @log_tool_call
    async def cancel_booking(
        self,
        ctx: RunContext,
        booking_index: Annotated[int, "The number of the booking from the list (1-based)"],
        phone_number: Annotated[str, "Customer's phone number to verify"]
    ) -> str:
        """
        Cancel a booking by its index from the list.
        Must call find_customer_bookings first.
        """
        phone_digits = ''.join(filter(str.isdigit, phone_number))
        
        # Get bookings again to find the right one
        bookings = await self.db.find_customer_bookings(phone_digits)
        
        if not bookings or booking_index < 1 or booking_index > len(bookings):
            return "I couldn't find that booking. Please ask me to look up your appointments first."
        
        target = bookings[booking_index - 1]
        booking_id = target['booking_id']
        
        success = await self.db.cancel_booking(booking_id, "Cancelled by customer via phone")
        
        if success:
            return f"Your {target['service_name']} appointment on {target['booking_date'].strftime('%A, %B %d')} has been cancelled. Is there anything else I can help with?"
        else:
            return "I had trouble cancelling that booking. Please try again."

    # --- 7. Reschedule ---

    @function_tool()
    @log_tool_call
    async def reschedule_booking(
        self,
        ctx: RunContext,
        booking_index: Annotated[int, "The number of the booking from the list (1-based)"],
        phone_number: Annotated[str, "Customer's phone number to verify"],
        new_date: Annotated[str, "New date for the appointment"],
        new_time: Annotated[str, "New time for the appointment"]
    ) -> str:
        """
        Reschedule a booking to a new date and time.
        Must call find_customer_bookings first.
        """
        phone_digits = ''.join(filter(str.isdigit, phone_number))
        
        # Get bookings
        bookings = await self.db.find_customer_bookings(phone_digits)
        
        if not bookings or booking_index < 1 or booking_index > len(bookings):
            return "I couldn't find that booking. Please ask me to look up your appointments first."
        
        target = bookings[booking_index - 1]
        
        # Parse new date/time
        try:
            p_date = parser.parse(new_date, fuzzy=True, default=datetime.now()).date()
            p_time = parser.parse(new_time, default=datetime.now()).time()
        except:
            return "I couldn't understand the new date or time. Please try again."
        
        if p_date < datetime.now().date():
            return "I cannot reschedule to a past date."
        
        # Calculate new end time (estimate 30 min if we don't have duration)
        duration = 30  # Default, ideally we'd look up the service duration
        end_dt = datetime.combine(p_date, p_time) + timedelta(minutes=duration)
        new_end_time = end_dt.time()
        
        # Update booking
        success = await self.db.reschedule_booking(
            target['booking_id'],
            p_date,
            p_time,
            new_end_time
        )
        
        if success:
            return f"Your appointment has been rescheduled to {p_date.strftime('%A, %B %d')} at {p_time.strftime('%I:%M %p')}. See you then!"
        else:
            return "I had trouble rescheduling. Please try again."

    # --- 8. General Queries ---

    @function_tool()
    @log_tool_call
    async def handle_general_query(
        self,
        ctx: RunContext,
        query: Annotated[str, "The user's general question"]
    ) -> str:
        """
        Handle general FAQs about hours, location, or policies.
        """
        q = query.lower()
        
        if "hour" in q or "open" in q or "time" in q or "close" in q:
            return "We're open Monday through Saturday from 9 AM to 7 PM. We're closed on Sundays."
        
        if "location" in q or "address" in q or "where" in q:
            return "We're located at 123 Beauty Lane, Downtown. There's free parking in the back."
        
        if "price" in q or "cost" in q or "how much" in q:
            return "Our prices vary by service. Would you like me to look up a specific service for you?"
        
        if "cancel" in q or "policy" in q:
            return "You can cancel or reschedule appointments up to 24 hours in advance. Just give me your phone number and I can help."
        
        return "I can help you book appointments, check our services, or answer questions. What would you like to do?"
