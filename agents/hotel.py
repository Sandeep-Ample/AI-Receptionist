"""
Hotel Agent - Luxury Resort Concierge

Example industry-specific agent for hospitality settings.
Demonstrates how to extend BaseReceptionist with hotel-specific tools.
"""

import asyncio
import logging
from typing import Annotated

from livekit.agents import RunContext, function_tool

from agents.base import BaseReceptionist
from agents.registry import register_agent
from prompts.templates import VOICE_FIRST_RULES

logger = logging.getLogger("hotel-agent")


@register_agent("hotel")
@register_agent("resort")
@register_agent("hospitality")
class HotelAgent(BaseReceptionist):
    """
    Luxury resort concierge for hotels and resorts.
    
    Handles:
    - Room reservations and inquiries
    - Amenity information
    - Local recommendations
    - Guest services
    """
    
    SYSTEM_PROMPT = f"""You are an elegant and attentive concierge at The Azure Vista Resort, a luxury beachfront property.

Your responsibilities:
- Assist guests with room reservations and booking modifications
- Provide information about hotel amenities and services
- Offer personalized local recommendations for dining and activities
- Handle special requests with grace and enthusiasm

Important guidelines:
- Exude warmth and sophistication in every interaction
- Anticipate guest needs and offer proactive suggestions
- For VIP guests, offer upgraded experiences when possible
- Always confirm details before finalizing any bookings

{VOICE_FIRST_RULES}"""

    GREETING_TEMPLATE = "Thank you for calling The Azure Vista Resort. How may I make your day exceptional?"
    RETURNING_GREETING_TEMPLATE = "Welcome back, {name}! It's wonderful to hear from you again. How may I assist you today?"

    @function_tool()
    async def check_room_availability(
        self,
        ctx: RunContext,
        check_in_date: Annotated[str, "Desired check-in date"],
        check_out_date: Annotated[str, "Desired check-out date"],
        room_type: Annotated[str, "Type of room: standard, deluxe, suite, or penthouse"] = "deluxe"
    ) -> str:
        """
        Check room availability for specific dates.
        Use this when a guest wants to make a new reservation.
        """
        logger.info(f"Checking availability: {check_in_date} to {check_out_date}, {room_type}")
        
        ctx.disallow_interruptions()
        ctx.session.say("Let me check our availability for those dates...")
        
        await asyncio.sleep(1.5)
        
        # Mock response
        rates = {"standard": 299, "deluxe": 449, "suite": 699, "penthouse": 1299}
        rate = rates.get(room_type.lower(), 449)
        
        return f"We have a beautiful {room_type} room available from {check_in_date} to {check_out_date} at ${rate} per night. This includes complimentary breakfast and spa access."

    @function_tool()
    async def make_reservation(
        self,
        ctx: RunContext,
        guest_name: Annotated[str, "The guest's full name"],
        check_in_date: Annotated[str, "Check-in date"],
        check_out_date: Annotated[str, "Check-out date"],
        room_type: Annotated[str, "Type of room"]
    ) -> str:
        """
        Create a new room reservation.
        Collect guest name, dates, and room preference.
        """
        logger.info(f"Making reservation: {guest_name}, {check_in_date}-{check_out_date}, {room_type}")
        
        ctx.disallow_interruptions()
        ctx.session.say("I'm completing your reservation now...")
        
        await asyncio.sleep(2.0)
        
        return f"Your reservation is confirmed, {guest_name}. {room_type.title()} room from {check_in_date} to {check_out_date}. A confirmation email with all details will arrive shortly."

    @function_tool()
    async def get_amenities(self, ctx: RunContext) -> str:
        """
        Describe the resort's amenities and facilities.
        Use this when guests ask what the hotel offers.
        """
        return "The Azure Vista features an infinity pool, full-service spa, three restaurants including a rooftop bar, private beach access, a fitness center, and complimentary yacht excursions on weekends."

    @function_tool()
    async def restaurant_recommendation(
        self,
        ctx: RunContext,
        cuisine_preference: Annotated[str, "Type of cuisine or dining experience desired"]
    ) -> str:
        """
        Recommend restaurants based on guest preferences.
        Use this for dining recommendations, both on-site and local.
        """
        logger.info(f"Restaurant recommendation for: {cuisine_preference}")
        
        ctx.session.say("I have some wonderful suggestions for you...")
        
        await asyncio.sleep(1.0)
        
        recommendations = {
            "italian": "Our on-site Bella Vista serves authentic Italian with ocean views. For local options, La Trattoria downtown is exceptional.",
            "seafood": "The Lighthouse on our rooftop offers the freshest catch daily. The local Captain's Table is also beloved by our guests.",
            "fine dining": "Azure on Five is our signature restaurant with a tasting menu by Chef Martinez. Reservations are recommended.",
            "casual": "The Beach House offers relaxed dining with toes in the sand. Perfect for a laid-back evening."
        }
        
        return recommendations.get(cuisine_preference.lower(), 
            f"For {cuisine_preference}, I'd recommend speaking with our concierge desk who can arrange a perfect dining experience.")

    @function_tool()
    async def book_spa_service(
        self,
        ctx: RunContext,
        guest_name: Annotated[str, "The guest's name"],
        service_type: Annotated[str, "Type of spa service: massage, facial, or package"],
        preferred_time: Annotated[str, "Preferred appointment time"]
    ) -> str:
        """
        Book a spa appointment for a guest.
        Collect service type and preferred time.
        """
        logger.info(f"Booking spa: {guest_name}, {service_type}, {preferred_time}")
        
        ctx.disallow_interruptions()
        ctx.session.say("I'm checking spa availability for you...")
        
        await asyncio.sleep(1.5)
        
        return f"Your {service_type} is booked for {preferred_time}, {guest_name}. Please arrive 15 minutes early to enjoy our relaxation lounge."
