"""
Agent Registry - Maps agent types to their classes.

The dispatcher in main.py uses this registry to instantiate
the correct agent class based on AGENT_TYPE environment variable
or job metadata.
"""

import logging
from typing import Type

from agents.base import BaseReceptionist

logger = logging.getLogger("receptionist-framework")

# Registry will be populated by imports
_AGENT_REGISTRY: dict[str, Type[BaseReceptionist]] = {}


def register_agent(agent_type: str):
    """
    Decorator to register an agent class with the registry.
    
    Usage:
        @register_agent("hospital")
        class HospitalAgent(BaseReceptionist):
            ...
    """
    def decorator(cls: Type[BaseReceptionist]):
        _AGENT_REGISTRY[agent_type.lower()] = cls
        logger.info(f"Registered agent type: {agent_type} -> {cls.__name__}")
        return cls
    return decorator


def get_agent_class(agent_type: str) -> Type[BaseReceptionist]:
    """
    Get the agent class for a given type.
    
    Args:
        agent_type: The agent type string (e.g., "hospital", "hotel")
    
    Returns:
        The agent class to instantiate
    
    Raises:
        ValueError: If the agent type is not registered
    """
    agent_type = agent_type.lower().strip()
    
    if agent_type in _AGENT_REGISTRY:
        return _AGENT_REGISTRY[agent_type]
    
    # Fallback to default if available
    if "default" in _AGENT_REGISTRY:
        logger.warning(f"Unknown agent type '{agent_type}', using default")
        return _AGENT_REGISTRY["default"]
    
    available = list(_AGENT_REGISTRY.keys())
    raise ValueError(
        f"Unknown agent type: '{agent_type}'. "
        f"Available types: {available}"
    )


def list_agent_types() -> list[str]:
    """Return list of all registered agent types."""
    return list(_AGENT_REGISTRY.keys())


# Import agents to trigger registration
# This must be at the bottom to avoid circular imports
def _load_agents():
    """Load all agent modules to trigger registration."""
    try:
        from agents import hospital, hotel, salon
        logger.info(f"Loaded {len(_AGENT_REGISTRY)} agent types: {list_agent_types()}")
    except ImportError as e:
        logger.warning(f"Some agents failed to load: {e}")


# Auto-load on module import
_load_agents()
