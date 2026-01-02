
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

    def attach(self, session: AgentSession):
        """
        automatically attach event listeners to the session.
        This captures transcripts and state changes without modifying main.py logic.
        """
        self.log("SYSTEM", "Attaching event listeners to session")
        
        @session.on("user_input_transcribed")
        def on_user_input(event):
            if event.is_final:
                self.log("TRANSCRIPT (USER)", event.transcript)
        
        @session.on("agent_speech_committed")
        def on_agent_speech(event):
            # Capture what the agent decided to say
            # Note: Event structure depends on SDK version, handling safely
            text = getattr(event, "text", str(event))
            self.log("TRANSCRIPT (AGENT)", text)
            
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
