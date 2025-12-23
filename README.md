# 🎙️ General Receptionist Framework

A modular, production-ready voice AI framework built on [LiveKit Agents](https://docs.livekit.io/agents/). Create industry-specific AI receptionists by extending a simple base class.

## ✨ Features

- **Modular Architecture** — Extend `BaseReceptionist` with your own agent
- **Persistent Memory** — PostgreSQL-backed caller recognition with warm greetings
- **Voice-First Design** — Optimized prompts for natural phone conversations
- **Built-in Tools** — `end_conversation`, `transfer_to_human`, `put_on_hold`
- **Interruption Protection** — Critical tool calls can't be broken by background noise

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.template .env
# Edit .env with your API keys

# 3. Start LiveKit server (Docker)
docker run --rm -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  livekit/livekit-server --dev

# 4. Run the agent
export AGENT_TYPE=hospital  # or hotel
python main.py dev

# 5. Open the UI
streamlit run app.py
```

## 📁 Project Structure

```
AI-Voice/
├── main.py              # Dispatcher (selects agent based on AGENT_TYPE)
├── app.py               # Streamlit web UI
├── agents/
│   ├── base.py          # BaseReceptionist class ⭐
│   ├── registry.py      # Agent type → class mapping
│   ├── hospital.py      # Example: Medical office
│   └── hotel.py         # Example: Resort concierge
├── memory/
│   ├── models.py        # PostgreSQL schema
│   └── service.py       # Async DB operations
├── tools/
│   └── common.py        # Shared tools
└── prompts/
    └── templates.py     # Voice-first prompt rules
```

## 🔧 Creating Your Own Agent

### Step 1: Create a new file

```python
# agents/restaurant.py
from typing import Annotated
from livekit.agents import RunContext, function_tool

from agents.base import BaseReceptionist
from agents.registry import register_agent
from prompts.templates import VOICE_FIRST_RULES


@register_agent("restaurant")
class RestaurantAgent(BaseReceptionist):
    """AI host for restaurants."""
    
    SYSTEM_PROMPT = f"""You are a friendly host at Bella Vista Restaurant.
    
You help guests with:
- Table reservations
- Menu inquiries  
- Hours and location

{VOICE_FIRST_RULES}"""

    GREETING_TEMPLATE = "Thank you for calling Bella Vista! How may I help you?"
    
    @function_tool()
    async def make_reservation(
        self,
        ctx: RunContext,
        party_size: Annotated[int, "Number of guests"],
        date: Annotated[str, "Reservation date"],
        time: Annotated[str, "Reservation time"]
    ) -> str:
        """Book a table for guests."""
        ctx.disallow_interruptions()  # Protect critical logic
        ctx.session.say("Let me check our availability...")
        
        # Your booking logic here
        return f"Table for {party_size} booked on {date} at {time}."
```

### Step 2: Import in registry

```python
# agents/registry.py — add to _load_agents()
from agents import hospital, hotel, restaurant
```

### Step 3: Run it

```bash
export AGENT_TYPE=restaurant
python main.py dev
```

## 🧠 Memory System (PostgreSQL)

Enable persistent caller memory for personalized greetings:

```bash
# Start PostgreSQL
docker run -d --name voice-pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=voice_agent \
  postgres:15

# Set connection string
export DATABASE_URL=postgresql://postgres:secret@localhost:5432/voice_agent
```

**What it does:**
1. Before first greeting → queries DB by caller ID
2. If found → greets by name: *"Hi Sarah, welcome back!"*
3. After call ends → saves 15-word summary asynchronously

**No database?** Framework works fine without it (no-memory mode).

## 🛠️ Built-in Tools

These tools are available to ALL agents:

| Tool | Description |
|------|-------------|
| `end_conversation` | Graceful goodbye + disconnect |
| `transfer_to_human` | Hand off to human operator |
| `put_on_hold` | Brief hold with verbal acknowledgment |

Import and use in your agent:
```python
from tools.common import COMMON_TOOLS
```

## 📝 Voice-First Prompt Rules

All agents automatically include these rules:

- ✅ Maximum 2 sentences per response
- ✅ No bullet points or formatting
- ✅ Natural verbal fillers: *"One moment..."*
- ✅ Conversational, warm, professional
- ❌ Never mention being an AI

## 🔌 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LIVEKIT_URL` | Yes | LiveKit server URL |
| `LIVEKIT_API_KEY` | Yes | LiveKit API key |
| `LIVEKIT_API_SECRET` | Yes | LiveKit API secret |
| `DEEPGRAM_API_KEY` | Yes | Deepgram STT API key |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `CARTESIA_API_KEY` | Yes | Cartesia TTS API key |
| `AGENT_TYPE` | No | Agent type (default: `hospital`) |
| `DATABASE_URL` | No | PostgreSQL connection string |

## 🧪 Testing Your Agent

```bash
# Quick import test
python -c "from agents.registry import list_agent_types; print(list_agent_types())"

# Run with debug logging
LOGLEVEL=DEBUG python main.py dev
```

## 📚 API Reference

### BaseReceptionist

```python
class BaseReceptionist(Agent):
    SYSTEM_PROMPT: str       # Override: Industry-specific instructions
    GREETING_TEMPLATE: str   # Override: Default greeting
    RETURNING_GREETING_TEMPLATE: str  # Override: Greeting for known callers
    
    def __init__(self, memory_context: Optional[dict] = None):
        """memory_context contains: name, last_summary, call_count"""
        
    async def on_enter(self):
        """Called when agent starts - sends greeting"""
        
    def get_caller_name(self) -> Optional[str]:
        """Get caller's name from memory"""
```

### @register_agent decorator

```python
@register_agent("my-agent")  # Registers with this key
@register_agent("alias")     # Can have multiple aliases
class MyAgent(BaseReceptionist):
    ...
```

### @function_tool decorator

```python
@function_tool()
async def my_tool(
    self,
    ctx: RunContext,
    param: Annotated[str, "Description for the LLM"]
) -> str:
    ctx.disallow_interruptions()  # Optional: prevent interruption
    ctx.session.say("Verbal filler...")  # Bridge latency gap
    # ... your logic
    return "Result for LLM"
```

## 🤝 Contributing

1. Fork the repository
2. Create your agent in `agents/`
3. Add tests
4. Submit a PR!

## 📄 License

MIT License - build whatever you want!

---

**Built with** ❤️ **using LiveKit Agents Framework**
