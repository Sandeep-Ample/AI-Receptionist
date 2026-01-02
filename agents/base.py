"""
BaseReceptionist - Core Engine for Voice Agents

This is the abstract base class that all industry-specific agents inherit from.
It handles all boilerplate: VAD, STT, LLM, TTS initialization, memory injection,
and common lifecycle methods.

Usage:
    class HospitalAgent(BaseReceptionist):
        SYSTEM_PROMPT = "You are a medical office receptionist..."
        GREETING_TEMPLATE = "Thank you for calling City Health Clinic..."
        
        @function_tool()
        async def check_appointment(self, ctx, patient_name: str):
            ...
"""

import logging
from abc import abstractmethod
from typing import Optional

from livekit.agents import Agent

from prompts.templates import build_prompt
from tools.common import COMMON_TOOLS

logger = logging.getLogger("receptionist-framework")


class BaseReceptionist(Agent):
    """
    Abstract base class for all industry-specific voice agents.
    
    Subclasses MUST override:
        - SYSTEM_PROMPT: Industry-specific instructions
    
    Subclasses MAY override:
        - GREETING_TEMPLATE: Default greeting for new callers
        - RETURNING_GREETING_TEMPLATE: Greeting for returning callers
        - get_tools(): Return list of industry-specific tools
    """
    
    # Override these in subclasses
    SYSTEM_PROMPT: str = "You are a helpful receptionist."
    GREETING_TEMPLATE: str = "Hello, thank you for calling! How can I help you today?"
    RETURNING_GREETING_TEMPLATE: str = "Hi {name}, welcome back! How can I help you today?"
    
    def __init__(self, memory_context: Optional[dict] = None):
        """
        Initialize the receptionist agent.
        
        Args:
            memory_context: Optional dict containing user memory from PostgreSQL.
                           Expected keys: 'name', 'last_summary', 'phone_number'
        """
        self.memory_context = memory_context
        
        # Build complete instructions with memory injection
        instructions = build_prompt(
            industry_prompt=self.SYSTEM_PROMPT,
            memory=memory_context,
            include_voice_rules=True
        )
        
        super().__init__(
            instructions=instructions,
            tools=COMMON_TOOLS
        )
        
        logger.info(f"Initialized {self.__class__.__name__} agent")
        if memory_context and memory_context.get("name"):
            logger.info(f"Returning user detected: {memory_context['name']}")
    
    async def on_enter(self):
        """
        Called when the agent starts. Sends appropriate greeting based on memory.
        
        - New callers get GREETING_TEMPLATE
        - Returning callers get personalized RETURNING_GREETING_TEMPLATE
        """
        if self.memory_context and self.memory_context.get("name"):
            # Returning user - personalized greeting
            name = self.memory_context["name"]
            greeting = self.RETURNING_GREETING_TEMPLATE.format(name=name)
            logger.info(f"Sending returning user greeting to {name}")
        else:
            # New caller - default greeting
            greeting = self.GREETING_TEMPLATE
            logger.info("Sending new caller greeting")
        
        try:
            logger.info(f"Attempting to say greeting: {greeting}")
            await self.session.say(greeting)
            logger.info("Greeting sent to audio buffer")
        except Exception as e:
            logger.error(f"Failed to say greeting: {e}", exc_info=True)
    
    def get_caller_name(self) -> Optional[str]:
        """Get the caller's name from memory, if available."""
        if self.memory_context:
            return self.memory_context.get("name")
        return None
    
    def get_last_summary(self) -> Optional[str]:
        """Get the last conversation summary from memory, if available."""
        if self.memory_context:
            return self.memory_context.get("last_summary")
        return None
