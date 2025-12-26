"""
Common Tools - Shared AI-callable tools for all agents.

These tools are available to all agent types and handle
common operations like ending conversations gracefully.
"""

import asyncio
import logging

from livekit.agents import RunContext, function_tool

logger = logging.getLogger("receptionist-framework")


@function_tool()
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
async def transfer_to_human(ctx: RunContext, reason: str) -> str:
    """
    Transfer the caller to a human operator.
    Call this when you cannot help the caller or they request a human.
    
    Args:
        reason: Brief reason for the transfer (e.g., "complex medical question")
    """
    logger.info(f"transfer_to_human called - reason: {reason}")
    
    ctx.disallow_interruptions()
    
    ctx.session.say(
        "I'll connect you with a team member who can better assist you. "
        "Please hold for just a moment."
    )
    
    # In a real implementation, this would trigger actual transfer logic
    # For now, we just log and acknowledge
    logger.info(f"Transfer requested: {reason}")
    
    return f"Transfer initiated: {reason}"



# List of common tools to include in all agents
COMMON_TOOLS = [
    end_conversation,
    transfer_to_human,
    put_on_hold,
]
