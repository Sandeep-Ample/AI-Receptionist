
"""
Universal Logger for Voice Agents
Records session transcripts, state changes, and events to text files.
"""
import os
import datetime
import logging
from typing import Optional

from livekit.agents import AgentSession, JobContext

# Fallback logger for errors in the logger itself
logger = logging.getLogger("universal-logger")

class UniversalLogger:
    """
    Logs comprehensive session details to a text file for debugging and tracing.
    """
    
    def __init__(self, job_id: str, agent_type: str = "unknown"):
        self.job_id = job_id
        
        # Ensure directory exists
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create log file: logs/YYYY-MM-DD_HH-MM-SS_jobID.txt
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.filename = os.path.join(self.log_dir, f"{timestamp}_{job_id}.txt")
        self.file = None
        
        try:
            self.file = open(self.filename, "a", encoding="utf-8")
            self._write_header(agent_type)
            logger.info(f"Session logging started: {self.filename}")
        except Exception as e:
            logger.error(f"Failed to create log file: {e}")

    def _write_header(self, agent_type: str):
        """Write session initialization details."""
        self.log_section("SESSION INITIALIZATION")
        self.log("Job ID", self.job_id)
        self.log("Agent Type", agent_type)
        self.log("Start Time", datetime.datetime.now().isoformat())
        self.log_separator()

    def log(self, category: str, message: str):
        """Write a standard log line."""
        if not self.file:
            return
            
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {category.upper()}: {message}\n"
        
        try:
            self.file.write(line)
            self.file.flush() # Ensure immediate write for debugging crashes
            
            # mirror to console for critical events
            if category in ("VAD", "TRANSCRIPT (USER)", "TRANSCRIPT (AGENT)", "ERROR"):
                logger.info(f"[{category}] {message}")
                
        except Exception as e:
            logger.error(f"Write error: {e}")

    def log_section(self, title: str):
        """Write a section header."""
        if not self.file:
            return
        self.file.write(f"\n{'='*20} {title.upper()} {'='*20}\n")
        self.file.flush()

    def log_separator(self):
        """Write a visual separator."""
        if not self.file:
            return
        self.file.write(f"{'-'*60}\n")
        self.file.flush()
        
    def close(self):
        """Close the log file."""
        if self.file:
            self.log_section("SESSION ENDED")
            self.log("End Time", datetime.datetime.now().isoformat())
            try:
                self.file.close()
            except:
                pass
            self.file = None



    async def _publish_update(self, session: AgentSession, type_str: str, text: str, speaker: str):
        """Send data to the frontend for UI rendering."""
        try:
            # Use stored room if available, otherwise try session.room (fallback)
            room = getattr(self, "room", None)
            if not room and hasattr(session, "room"):
                room = session.room
                
            if not room:
                return # Cannot publish without room
                
            import json
            payload = json.dumps({
                "type": type_str,
                "text": text,
                "speaker": speaker,
                "timestamp": datetime.datetime.now().isoformat()
            })
            # Publish to the room so the frontend (Streamlit) receives it
            await room.local_participant.publish_data(
                payload.encode('utf-8'),
                reliable=True
            )
        except Exception as e:
            logger.error(f"Failed to publish data update: {e}")

    def attach(self, session: AgentSession, room=None):
        """
        automatically attach event listeners to the session.
        This captures transcripts and state changes without modifying main.py logic.
        """
        self.log("SYSTEM", "Attaching event listeners to session")
        self.room = room
        
        @session.on("user_speech_committed")
        def on_user_speech(event):
             # Log speech commit (VAD determined speech happened)
             self.log("VAD", "User speech committed (processing...)")
             pass

        @session.on("user_input_transcribed")
        def on_user_input(event):
            if event.is_final:
                text = event.transcript
                self.log("TRANSCRIPT (USER)", text)
                # Publish to UI
                import asyncio
                asyncio.create_task(self._publish_update(session, "transcription", text, "user"))
        
        @session.on("speech_started")
        def on_speech_started(event):
             # This event acts as a backup/faster trigger for agent transcripts
             # It might not carry the full text, but let's check.
             # Actually, 'conversation_item_added' is usually the source of truth for the text,
             # but it might be fired LATE (after generation).
             # Let's try to get text from speech_created if available, but usually that's just a handle.
             pass
        
        @session.on("conversation_item_added")
        def on_conversation_item(event):
            # This event fires for both user and agent messages
            item = getattr(event, "item", None)
            if item is None:
                return
            
            role = getattr(item, "role", None)
            content = getattr(item, "content", None)
            
            # Only process assistant (agent) messages here, user messages are handled by user_input_transcribed
            if role == "assistant" and content:
                # Handle content that might be a list
                text = content if isinstance(content, str) else " ".join(str(c) for c in content)
                if text and text.strip():
                    self.log("TRANSCRIPT (AGENT)", text)
                    # Publish to UI
                    import asyncio
                    asyncio.create_task(self._publish_update(session, "transcription", text, "agent"))
            
        @session.on("agent_state_changed")
        def on_state_change(event):
            new_state = getattr(event, "new_state", "unknown")
            self.log("STATE CHANGE", str(new_state))

        # We can also spy on function calls if we had a mechanism, 
        # but for now we track the main visible events.
        
    def log_tool_call(self, tool_name: str, args: dict, result: str):
        """Log a tool execution event."""
        self.log_separator()
        self.log("TOOL CALL", f"Executing: {tool_name}")
        self.log("TOOL ARGS", str(args))
        self.log("TOOL RESULT", str(result))
        self.log_separator()


import functools
import inspect

def log_tool_call(func):
    """
    Decorator to automatically log tool inputs and outputs.
    Requires that the first argument 'ctx' has a 'session' attribute,
    and that session object has a 'universal_logger' attribute.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 1. Inspect arguments to find tool name and parameter values
        tool_name = func.__name__
        
        # Safe argument extraction
        try:
             # Bind arguments to signature to get effective kwargs
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            all_args = bound_args.arguments
            
            # Filter out 'self' and 'ctx' from logged parameters for cleanliness
            clean_args = {k: v for k, v in all_args.items() if k not in ("self", "ctx")}
        except Exception:
            clean_args = kwargs # Fallback
            
        # 2. Extract logger if available
        # We expect the first arg to be 'ctx' for tools, or 'self' then 'ctx'
        ctx = None
        for arg in args:
            if hasattr(arg, "session"):
                ctx = arg
                break
        
        logger_instance = None
        if ctx and hasattr(ctx.session, "universal_logger"):
            logger_instance = ctx.session.universal_logger

        # 3. Execute the tool
        result = await func(*args, **kwargs)
        
        # 4. Log the result
        if logger_instance:
            try:
                # Truncate long results
                log_result = str(result)
                if len(log_result) > 500:
                    log_result = log_result[:500] + "... (truncated)"
                    
                logger_instance.log_tool_call(tool_name, clean_args, log_result)
            except Exception as e:
                logger.error(f"Failed to log tool call: {e}")
                
        return result
        
    return wrapper
