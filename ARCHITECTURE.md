# Code Architecture Guide

A deep dive into how the General Receptionist Framework works internally.

---

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. python main.py dev                                          │
│     └──> cli.run_app() starts LiveKit worker                   │
│                                                                 │
│  2. prewarm() loads Silero VAD model into proc.userdata        │
│                                                                 │
│  3. User connects via Streamlit UI                              │
│     └──> LiveKit dispatches job to entrypoint()                │
│                                                                 │
│  4. entrypoint() flow:                                          │
│     ├── Read AGENT_TYPE from env                                │
│     ├── Connect to room, wait for participant                   │
│     ├── Fetch memory from PostgreSQL (if enabled)               │
│     ├── Get agent class from registry                           │
│     ├── Instantiate agent with memory_context                   │
│     ├── Create AgentSession (VAD + STT + LLM + TTS)            │
│     ├── Start session, agent.on_enter() sends greeting          │
│     └── Loop until disconnect, then async save summary          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Files Explained

### main.py — The Dispatcher

```python
# Key responsibilities:
# 1. Determine agent type from AGENT_TYPE env var
# 2. Fetch user memory before greeting
# 3. Instantiate correct agent class
# 4. Manage session lifecycle
# 5. Save summary asynchronously on disconnect

async def entrypoint(ctx: JobContext):
    agent_type = os.getenv("AGENT_TYPE", "default")
    
    # Memory fetch (before first greeting)
    memory = await memory_service.fetch_user(caller_id)
    
    # Registry lookup
    AgentClass = get_agent_class(agent_type)  # Returns HospitalAgent, HotelAgent, etc.
    agent = AgentClass(memory_context=memory)
    
    # Session = VAD + STT + LLM + TTS pipeline
    session = AgentSession(...)
    await session.start(agent=agent, room=ctx.room, ...)
```

---

### agents/base.py — The Core Engine

```python
class BaseReceptionist(Agent):
    """
    Abstract base class. Subclasses only need to provide:
    - SYSTEM_PROMPT: str
    - GREETING_TEMPLATE: str  
    - Tools via @function_tool()
    """
    
    def __init__(self, memory_context=None):
        # Build prompt WITH memory injection
        instructions = build_prompt(
            industry_prompt=self.SYSTEM_PROMPT,
            memory=memory_context  # {"name": "Sarah", "last_summary": "..."}
        )
        super().__init__(instructions=instructions)
    
    async def on_enter(self):
        # Called when agent starts - sends personalized greeting
        if self.memory_context and self.memory_context.get("name"):
            self.session.say(f"Hi {name}, welcome back!")
        else:
            self.session.say(self.GREETING_TEMPLATE)
```

---

### agents/registry.py — Agent Type Mapping

```python
_AGENT_REGISTRY = {}  # Global registry dict

def register_agent(agent_type: str):
    """Decorator that registers agent classes."""
    def decorator(cls):
        _AGENT_REGISTRY[agent_type.lower()] = cls
        return cls
    return decorator

# Usage in hospital.py:
@register_agent("hospital")
@register_agent("default")  # Multiple aliases allowed
class HospitalAgent(BaseReceptionist):
    ...

# Lookup:
get_agent_class("hospital")  # Returns HospitalAgent class
```

---

### prompts/templates.py — Voice-First Rules

```python
VOICE_FIRST_RULES = """
CRITICAL VOICE RULES:
1. Maximum 2 sentences per response
2. No bullet points, lists, or formatting
3. Use verbal acknowledgments: "One moment..."
...
"""

def build_prompt(industry_prompt, memory=None):
    """
    Combines:
    1. Industry-specific prompt (from agent's SYSTEM_PROMPT)
    2. Voice-first rules (always included)
    3. Memory context (if returning caller)
    
    Result is the full system prompt sent to the LLM.
    """
    parts = [industry_prompt, VOICE_FIRST_RULES]
    
    if memory and memory.get("name"):
        parts.append(f"RETURNING USER: {memory['name']}. Last: {memory['last_summary']}")
    
    return "\n\n".join(parts)
```

---

### memory/service.py — PostgreSQL Operations

```python
class MemoryService:
    """Async PostgreSQL with connection pooling."""
    
    async def fetch_user(self, caller_id: str) -> Optional[dict]:
        """
        Called BEFORE agent greeting.
        Returns: {"name": "Sarah", "last_summary": "Asked about dental checkup", ...}
        """
        row = await conn.fetchrow(FETCH_USER_SQL, caller_id)
        return dict(row) if row else None
    
    async def save_user(self, caller_id, name, summary):
        """
        Called AFTER call ends (async, non-blocking).
        Upserts user record with new summary.
        """
        await conn.execute(UPSERT_USER_SQL, caller_id, name, summary)

# Singleton pattern
_memory_service = None
def get_memory_service():
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
```

---

### tools/common.py — Shared AI Tools

```python
@function_tool()
async def end_conversation(ctx: RunContext) -> str:
    """LLM calls this when customer is satisfied."""
    
    ctx.disallow_interruptions()  # Can't be stopped by noise
    ctx.session.say("Thank you for calling! Goodbye!")
    await asyncio.sleep(3.0)  # Wait for audio
    await ctx.session.aclose()  # Disconnect
    
    return "Conversation ended"

# ctx.disallow_interruptions() — Prevents VAD from cutting off during critical logic
# ctx.session.say() — Immediately speaks text via TTS
# ctx.session.aclose() — Graceful session shutdown
```

---

### agents/hospital.py — Example Industry Agent

```python
@register_agent("hospital")
class HospitalAgent(BaseReceptionist):
    
    SYSTEM_PROMPT = """You are a medical office receptionist..."""
    GREETING_TEMPLATE = "Thank you for calling City Health Clinic!"
    
    @function_tool()
    async def check_appointment(
        self,
        ctx: RunContext,
        patient_name: Annotated[str, "The patient's full name"]  # LLM sees this description
    ) -> str:
        """Look up appointments."""  # LLM sees this docstring
        
        ctx.disallow_interruptions()
        ctx.session.say("One moment...")  # Verbal filler
        
        await asyncio.sleep(1.5)  # Simulate DB lookup
        
        return "Found appointment for Friday at 2:30 PM"  # LLM uses this in response
```

**Tool Flow:**
1. User: "Do I have any appointments?"
2. LLM decides to call `check_appointment` tool
3. Tool runs: says "One moment...", does lookup
4. Tool returns result string to LLM
5. LLM formulates response: "Yes, you have an appointment Friday at 2:30 PM"

---

## Data Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │ Deepgram │     │  OpenAI  │     │ Cartesia │
│  Audio   │────>│   STT    │────>│   LLM    │────>│   TTS    │────> Audio Out
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  @function_tool  │
                              │  (your tools)    │
                              └──────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │   PostgreSQL     │
                              │   (memory)       │
                              └──────────────────┘
```

---

## Key Patterns

### 1. Decorator-Based Registration
```python
@register_agent("type")  # Adds to global registry at import time
class MyAgent(BaseReceptionist):
    ...
```

### 2. Memory Injection
```python
# Memory fetched BEFORE agent init
memory = await service.fetch_user(caller_id)

# Passed to agent constructor
agent = HospitalAgent(memory_context=memory)

# Injected into system prompt in BaseReceptionist.__init__()
```

### 3. Async Summarization (Fire & Forget)
```python
finally:
    # Don't await - let user disconnect immediately
    asyncio.create_task(_save_summary_async(session, caller_id))
```

### 4. Interruption Protection
```python
@function_tool()
async def critical_operation(ctx):
    ctx.disallow_interruptions()  # VAD won't cut this off
    # ... safe to do multi-step operations
```

---

## Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `AGENT_TYPE` | main.py | Selects agent class |
| `DATABASE_URL` | memory/service.py | PostgreSQL connection |
| `DEEPGRAM_API_KEY` | livekit-plugins-deepgram | STT |
| `OPENAI_API_KEY` | livekit-plugins-openai | LLM |
| `CARTESIA_API_KEY` | livekit-plugins-cartesia | TTS |

---

## Adding a New Feature

**Example: Add call recording**

1. Create `recording/service.py`
2. Import in `main.py`
3. Call `await recording.start()` after session starts
4. Call `await recording.stop()` in finally block

**Example: Add new common tool**

1. Add function to `tools/common.py`
2. Decorate with `@function_tool()`
3. Add to `COMMON_TOOLS` list
4. Tools are automatically available to all agents

---

## Debugging Tips

```bash
# Verbose logging
LOGLEVEL=DEBUG python main.py dev

# Test registry without running agent
python -c "from agents.registry import list_agent_types; print(list_agent_types())"

# Test memory service
python -c "
import asyncio
from memory.service import get_memory_service
async def test():
    svc = get_memory_service()
    await svc.initialize()
    print(await svc.fetch_user('test'))
asyncio.run(test())
"
```
