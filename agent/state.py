from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
from datetime import datetime


class Lead(BaseModel):
    """Represents a sales lead/contact"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    email: Optional[str] = None
    company: Optional[str] = None


class ConversationState(BaseModel):
    """
    Conversation state that flows through the LangGraph graph.
    
    This holds all evolving information during the call, including:
    - Current phase/intent of the conversation
    - Lead information
    - Extracted slots (datetime, preferences, etc.)
    - Tone and context
    - Whether the call is done
    - Last agent reply for display/debugging
    """
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # high-level conversational info
    phase: str = "intro"  
    # intro | qualify | schedule | confirm | closing OR next_action ("propose_meeting", etc.)

    intent: Optional[str] = None  
    # interested | busy | send_info | not_interested | question | unclear

    tone: Optional[str] = None    
    # friendly | rushed | skeptical | shut_down | curious
    
    tone_confidence: Optional[float] = None
    # Confidence score for tone detection (0.0 to 1.0)

    lead: Lead
    
    # Conversation history (for context across turns)
    conversation_history: list = Field(default_factory=list)
    # List of {"user": str, "agent": str, "intent": str, "tone": str, "turn": int}

    # useful slots we fill along the way
    slots: Dict[str, Any] = Field(default_factory=dict)
    # Separate date and time slots for better handling:
    # slots["date_slot"]: Optional[str] - date part ("later today", "tomorrow", "next week")
    # slots["time_slot"]: Optional[str] - time part ("6pm", "after work", "2pm")
    # slots["datetime"]: Optional[datetime] - parsed full datetime object (when both slots filled)
    # slots["channel_pref"]: Optional[str]  # "sms" or "email"
    # slots["confirmation"]: Optional[bool] - whether they confirmed scheduling

    done: bool = False

    # last line the agent spoke (for debugging / display in demo loop)
    last_agent_reply: Optional[str] = None
    
    # current user utterance (set by the graph runtime)
    current_user_utterance: Optional[str] = None

