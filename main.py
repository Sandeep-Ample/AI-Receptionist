"""
LiveKit Voice Agent - General Receptionist Framework
Main entry point / dispatcher for industry-specific voice agents.

Usage:
    # Set agent type via environment variable
    export AGENT_TYPE=hospital  # or hotel, clinic, resort, etc.
    python main.py dev

AI Stack:
- STT: Deepgram (nova-2)
- LLM: OpenAI GPT-4o-mini  
- TTS: Cartesia (sonic-2)
- VAD: Silero

Framework Features:
- Modular industry-specific agents via registry
- PostgreSQL persistent memory for returning callers
- Voice-first prompts with warm-up greetings
- Async summarization on call end
"""

import asyncio
import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
# Try to import RoomOptions, fallback to RoomInputOptions alias if needed
try:
    from livekit.agents import RoomOptions
except ImportError:
    RoomOptions = RoomInputOptions
from livekit.plugins import cartesia, deepgram, openai, silero

# Framework imports
from agents.registry import get_agent_class, list_agent_types
from memory.service import get_memory_service
from tools.common import COMMON_TOOLS
from tools.session_logger import UniversalLogger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("receptionist-framework")


def prewarm(proc: JobProcess):
    """Prewarm function to load models before the agent starts."""
    logger.info("Prewarming: Loading Silero VAD model...")
    proc.userdata["vad"] = silero.VAD.load(min_speech_duration=0.2, activation_threshold=0.4)
    logger.info(f"Prewarming complete. Available agents: {list_agent_types()}")


async def _generate_summary(session: AgentSession) -> Optional[str]:
    """
    Generate a concise 15-word summary of the conversation using the LLM.
    
    Args:
        session: The agent session with chat context
        
    Returns:
        A brief summary string or None if generation fails
    """
    try:
        # Build a summary prompt from the conversation
        if not session.current_agent or not session.current_agent.chat_ctx:
             return None
        messages = session.current_agent.chat_ctx.items
        if len(messages) < 2:
            return None
        
        # Create a simple transcript - filter out FunctionCall objects
        transcript_parts = []
        for msg in messages:
            # Skip items that don't have a role attribute (e.g., FunctionCall)
            if not hasattr(msg, 'role') or not hasattr(msg, 'content'):
                continue
            if msg.role in ("user", "assistant") and msg.content:
                role = "Caller" if msg.role == "user" else "Agent"
                # Handle content that might be a list
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                transcript_parts.append(f"{role}: {content}")
        
        if not transcript_parts:
            return None
        
        transcript = "\n".join(transcript_parts[-10:])  # Last 10 exchanges
        
        # Use a quick LLM call to summarize
        llm = openai.LLM(model="gpt-4o-mini")
        
        summary_prompt = f"""Summarize this phone call in exactly 15 words or less.
Focus on: what the caller needed and the outcome.

Transcript:
{transcript}

Summary:"""

        # Quick non-streaming call
        response = await llm.chat(
            chat_ctx=None,
            messages=[{"role": "user", "content": summary_prompt}]
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"Generated summary: {summary}")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return None


async def _save_summary_async(session: AgentSession, caller_id: str, caller_name: Optional[str]):
    """
    Async task to generate summary and save to database.
    This runs in the background so the agent can hang up immediately.
    """
    try:
        memory_service = get_memory_service()
        
        # Generate summary
        summary = await _generate_summary(session)
        
        if summary:
            # Save to database
            await memory_service.save_user(
                caller_id=caller_id,
                name=caller_name,
                summary=summary
            )
            logger.info(f"Saved conversation summary for {caller_id}")
        else:
            logger.info("No summary generated - conversation too short")
            
        # Log conversation history (async to avoid blocking entrypoint exit)
        logger.info("=" * 40)
        logger.info("CONVERSATION HISTORY")
        if session.current_agent and session.current_agent.chat_ctx:
            for msg in session.current_agent.chat_ctx.items:
                # Skip items that don't have a role attribute (e.g., FunctionCall)
                if not hasattr(msg, 'role'):
                    continue
                content = msg.content if hasattr(msg, 'content') else "[no content]"
                # Handle content that might be a list
                if isinstance(content, list):
                    content = ' '.join(str(c) for c in content)
                logger.info(f"[{msg.role.upper()}]: {content}")
        logger.info("=" * 40)

    except Exception as e:
        logger.error(f"Error in async summary save: {e}")


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the voice agent framework."""
    
    # 1. Determine which agent type to use
    agent_type = os.getenv("AGENT_TYPE", "default")
    
    # Can also get from job metadata if passed from dispatch
    if ctx.job and ctx.job.metadata:
        try:
            metadata = json.loads(ctx.job.metadata)
            agent_type = metadata.get("agent_type", agent_type)
        except (json.JSONDecodeError, TypeError):
            pass
    
    logger.info(f"Starting agent type: {agent_type}")
    
    # Initialize Universal Logger
    session_logger = UniversalLogger(job_id=ctx.job.id, agent_type=agent_type)
    session_logger.log("SYSTEM", "Logger initialized and starting connection sequence")
    
    # 2. Connect to the room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # 3. Wait for participant
    participant = await ctx.wait_for_participant()
    caller_id = participant.identity
    logger.info(f"Participant joined: {caller_id}")
    
    # 4. Fetch memory from PostgreSQL (if enabled)
    memory_service = get_memory_service()
    await memory_service.initialize()
    memory = await memory_service.fetch_user(caller_id)
    
    if memory:
        logger.info(f"Returning caller: {memory.get('name')} (call #{memory.get('call_count', 1)})")
    else:
        logger.info("New caller - no memory found")
    
    # 5. Instantiate the correct agent with memory context
    AgentClass = get_agent_class(agent_type)
    agent = AgentClass(memory_context=memory, caller_identity=caller_id)
    logger.info(f"Instantiated agent: {AgentClass.__name__} for caller: {caller_id}")
    
    # 6. Create session with optimized settings
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=cartesia.TTS(),
        allow_interruptions=True,
    )
    
    # Track caller name for summary
    caller_name = memory.get("name") if memory else None
    
    try:
        # 7. Set up event handlers
        session_logger.attach(session, room=ctx.room)
        # Attach logger to session for tools to access
        session.universal_logger = session_logger
        
        
        @session.on("user_input_transcribed")
        def on_user_input(event):
            if event.is_final:
                logger.info(f"User: {event.transcript}")
                # Try to extract name if we don't have it
                nonlocal caller_name
                if not caller_name and "my name is" in event.transcript.lower():
                    # Simple name extraction
                    parts = event.transcript.lower().split("my name is")
                    if len(parts) > 1:
                        name = parts[1].strip().split()[0].title()
                        caller_name = name
                        logger.info(f"Extracted caller name: {name}")
        
        @session.on("agent_state_changed")
        def on_state_changed(event):
            logger.debug(f"Agent state: {event.new_state}")
        
        # 8. Start the agent session
        await session.start(
            agent=agent,
            room=ctx.room,
            # Disable auto-close to handle it manually with drain=False
            room_input_options=RoomOptions(
                participant_identity=caller_id,
                close_on_disconnect=False,
            ),
        )
        logger.info("Voice agent started successfully")
        
        # 9. Keep alive while connected
        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(0.1)

        logger.info("Disconnected - shutting down session immediately")
        session.shutdown(drain=False)
            
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        
    finally:
        session_logger.log("SYSTEM", "Session cleanup initiated")
        session_logger.close()
        
        # 10. Explicitly disconnect to ensure immediate room departure
        # This fixes issues where the agent lingers in the room (15s timeout)
        try:
            if ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                 logger.info("Explicitly disconnecting from room...")
                 await ctx.room.disconnect()
        except Exception as e:
            logger.error(f"Error during explicit disconnect: {e}")

        # 11. Run summarization *after* disconnect
        # We await it here to ensure the process stays alive until it's done.
        logger.info("Session ending - running summary generation...")
        try:
            await _save_summary_async(session, caller_id, caller_name)
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
        
        # Print conversation for debugging
        
        # Print conversation for debugging moved to async task



if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
