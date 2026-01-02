"""
Common Tools - Shared AI-callable tools for all agents.

These tools are available to all agent types and handle
common operations like ending conversations gracefully.
"""

import asyncio
import logging

from livekit.agents import RunContext, function_tool

from typing import Annotated, Optional
from memory.service import get_memory_service

logger = logging.getLogger("receptionist-framework")
from tools.session_logger import log_tool_call


@function_tool()
@log_tool_call
async def end_conversation(ctx: RunContext) -> str:
    """
    End the conversation gracefully when the customer's needs are met.
    Call this tool when the caller is satisfied and ready to hang up.
    
    This will:
    1. Say a polite goodbye
    2. Wait for audio to finish playing
    3. Gracefully disconnect the session
    """
    logger.info("end_conversation tool called - initiating graceful disconnect")
    
    # Protect this critical operation from interruptions
    ctx.disallow_interruptions()
    
    # Say goodbye
    ctx.session.say("Thank you for calling! Have a wonderful day. Goodbye!")
    
    # Wait for the goodbye audio to play out
    await asyncio.sleep(3.0)
    
    # Gracefully close the session
    try:
        await ctx.session.aclose()
        logger.info("Session closed gracefully")
    except Exception as e:
        logger.error(f"Error closing session: {e}")
    
    return "Conversation ended gracefully"


@function_tool()
@log_tool_call
async def update_user_info(
    ctx: RunContext,
    name: Annotated[Optional[str], "The user's preferred name"] = None,
    note: Annotated[Optional[str], "A brief piece of info to remember (e.g., 'allergic to penicillin')"] = None
) -> str:
    """
    Update the caller's persistent profile. 
    Call this as soon as the user reveals their name or an important preference.
    """
    caller_id = ctx.participant.identity
    memory_service = get_memory_service()
    
    # Prepare metadata (this will be merged into the existing JSONB in Postgres)
    metadata = {"note": note} if note else {}
    
    success = await memory_service.save_user(
        caller_id=caller_id,
        name=name,
        metadata=metadata
    )
    
    if success:
        return f"Updated profile for {caller_id}. I will remember this for future calls."
    return "I couldn't save that information right now."



# List of common tools to include in all agents
COMMON_TOOLS = [
    end_conversation,
    update_user_info
]
