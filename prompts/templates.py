"""
Voice-First Prompt Templates

These templates enforce conversational, voice-optimized responses
for AI voice agents. No formatting, short sentences, natural speech.
"""

# Core voice-first rules that MUST be included in every agent prompt
VOICE_FIRST_RULES = """
CRITICAL VOICE RULES - YOU MUST FOLLOW THESE:
1. Maximum 2 sentences per response - be concise
2. No bullet points, numbered lists, or any formatting
3. No bold, italic, asterisks, or special characters
4. Use natural verbal acknowledgments before delays: "One moment...", "Let me check that..."
5. Be conversational, warm, and professional
6. Speak naturally as if on a phone call
7. Never say "I'm an AI" or mention being a language model
"""

# Memory injection template for returning users
MEMORY_INJECTION_TEMPLATE = """
RETURNING USER CONTEXT:
- User's name: {name}
- Last conversation summary: {last_summary}
- You MUST greet them by name and reference their last visit naturally.
- Example: "Hi {name}, welcome back! Are you calling about {topic_hint}?"
"""


from typing import Optional


def build_prompt(
    industry_prompt: str, 
    memory: Optional[dict] = None,
    include_voice_rules: bool = True
) -> str:
    """
    Build a complete system prompt combining:
    - Industry-specific instructions
    - Voice-first rules
    - Memory context (if returning user)
    
    Args:
        industry_prompt: The industry-specific system prompt
        memory: Optional dict with 'name' and 'last_summary' keys
        include_voice_rules: Whether to include voice-first rules (default: True)
    
    Returns:
        Complete system prompt string
    """
    parts = [industry_prompt.strip()]
    
    # Add voice-first rules
    if include_voice_rules:
        parts.append(VOICE_FIRST_RULES.strip())
    
    # Add memory context for returning users
    if memory and memory.get("name"):
        last_summary = memory.get("last_summary", "their previous inquiry")
        # Extract a topic hint from the summary
        topic_hint = _extract_topic_hint(last_summary)
        
        memory_context = MEMORY_INJECTION_TEMPLATE.format(
            name=memory["name"],
            last_summary=last_summary,
            topic_hint=topic_hint
        )
        parts.append(memory_context.strip())
    
    return "\n\n".join(parts)


def _extract_topic_hint(summary: str) -> str:
    """
    Extract a brief topic hint from the last conversation summary.
    Used for the warm-up greeting.
    """
    if not summary or len(summary) < 10:
        return "what we discussed last time"
    
    # Take first ~30 chars as topic hint, clean up
    hint = summary[:50].strip()
    if len(summary) > 50:
        # Find a good break point
        for sep in [",", ".", " - ", " and "]:
            if sep in hint:
                hint = hint.split(sep)[0].strip()
                break
        hint = hint.rstrip(".,;:")
    
    return hint.lower() if hint else "what we discussed last time"
