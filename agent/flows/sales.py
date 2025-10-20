from typing import Dict, Any, List
from datetime import datetime, timedelta
from agent.schemas import SessionState, ToolCall
from agent.nlu import parse


# System prompt for future LLM use
SALES_SYSTEM_PROMPT = """
You are a professional AI sales agent calling prospects about our AI call agent service. 
Your goal is to:
1. Introduce our AI call agent that books demos for sales teams
2. Gauge interest and schedule follow-up calls
3. Handle objections professionally
4. Always be polite and respectful

Key talking points:
- Our AI agent handles initial sales calls automatically
- It can qualify leads and book demos
- Saves sales reps time on cold calling
- Increases conversion rates

Always ask for permission before scheduling and respect "do not call" requests.
"""


def next_agent_reply(state: SessionState, user_utterance: str) -> Dict[str, Any]:
    """
    Determine the next agent reply based on current state and user input
    
    Returns:
        Dict with "reply", "tool_calls", "final" keys
    """
    # Parse user intent and slots
    intent, slots = parse(user_utterance, state.lead)
    
    # Update state slots
    state.slots.update(slots)
    
    # Determine response based on conversation state
    if len(state.history) == 0:
        # First interaction - greeting and pitch
        return _handle_greeting(state)
    
    # Get the last agent message to understand context
    last_turn = state.history[-1] if state.history else None
    last_agent_msg = last_turn.agent if last_turn else ""
    
    # Handle different intents with conversation context
    if "confirmation" in state.slots:
        # If we're waiting for confirmation, handle that first
        return _handle_confirmation(state, user_utterance)
    elif intent == "interested":
        return _handle_interested(state, user_utterance)
    elif intent == "busy":
        return _handle_busy(state, user_utterance)
    elif intent == "send_info":
        return _handle_send_info(state, user_utterance)
    elif intent == "reject":
        return _handle_reject(state, user_utterance)
    elif intent == "schedule_followup":
        # Check if we're in an interested conversation context
        if _is_interested_context(state):
            # User is providing time for a demo, not just a follow-up
            return _schedule_demo_meeting(state)
        else:
            return _handle_schedule_followup(state, user_utterance)
    else:
        return _handle_unknown(state, user_utterance)


def _is_interested_context(state: SessionState) -> bool:
    """Check if we're in an interested conversation context"""
    if not state.history:
        return False
    
    # Look at the last agent message to see if we're asking for demo time
    last_turn = state.history[-1]
    last_agent_msg = last_turn.agent.lower()
    
    # Check if the agent was asking for demo scheduling time
    interested_indicators = [
        "schedule a quick demo",
        "demo call",
        "when would work best",
        "tomorrow afternoon or next week"
    ]
    
    return any(indicator in last_agent_msg for indicator in interested_indicators)


def _handle_greeting(state: SessionState) -> Dict[str, Any]:
    """Handle initial greeting and pitch"""
    lead_name = state.lead.name if state.lead else "there"
    
    reply = f"""Hi {lead_name}, this is your AI sales agent calling about our AI call agent that books demos for you automatically. 

Our AI agent can handle your initial sales calls, qualify leads, and schedule follow-up meetings, so you can spend more time closing deals instead of dialing numbers.

Are you interested in learning more about how this could help your sales team?"""
    
    return {
        "reply": reply,
        "tool_calls": [],
        "final": False
    }


def _handle_interested(state: SessionState, utterance: str) -> Dict[str, Any]:
    """Handle when user shows interest"""
    if "parsed_datetime" in state.slots:
        # User provided a specific time - schedule demo meeting
        return _schedule_demo_meeting(state)
    else:
        # Ask for time preference
        reply = "Great! I'd love to schedule a quick demo call. When would work best for you? For example, tomorrow afternoon or next week?"
        return {
            "reply": reply,
            "tool_calls": [],
            "final": False
        }


def _handle_busy(state: SessionState, utterance: str) -> Dict[str, Any]:
    """Handle when user is busy"""
    if "parsed_datetime" in state.slots:
        # User provided a specific time for follow-up
        return _schedule_followup(state)
    else:
        reply = "No problem! When would be a better time for me to call you back? I can schedule a follow-up call."
        return {
            "reply": reply,
            "tool_calls": [],
            "final": False
        }


def _handle_send_info(state: SessionState, utterance: str) -> Dict[str, Any]:
    """Handle when user wants information sent"""
    reply = "I'd be happy to send you more information. Would you prefer I email you the details or send you a text with a link to our demo?"
    
    # Log the request in CRM
    tool_calls = [ToolCall(
        name="crm_stub.log_outcome",
        args={
            "lead": state.lead.dict() if state.lead else {},
            "outcome": "requested_info",
            "meta": {"preference": "email_or_sms"}
        }
    )]
    
    return {
        "reply": reply,
        "tool_calls": tool_calls,
        "final": False
    }


def _handle_reject(state: SessionState, utterance: str) -> Dict[str, Any]:
    """Handle rejection politely"""
    reply = "I completely understand. Thank you for your time, and I'll make sure you're not contacted again. Have a great day!"
    
    # Log the rejection
    tool_calls = [ToolCall(
        name="crm_stub.log_outcome",
        args={
            "lead": state.lead.dict() if state.lead else {},
            "outcome": "rejected",
            "meta": {"reason": utterance}
        }
    )]
    
    return {
        "reply": reply,
        "tool_calls": tool_calls,
        "final": True
    }


def _handle_schedule_followup(state: SessionState, utterance: str) -> Dict[str, Any]:
    """Handle scheduling follow-up"""
    if "parsed_datetime" in state.slots:
        return _schedule_followup(state)
    else:
        reply = "Perfect! When would you like me to call you back? Please let me know a specific day and time."
        return {
            "reply": reply,
            "tool_calls": [],
            "final": False
        }


def _handle_confirmation(state: SessionState, utterance: str) -> Dict[str, Any]:
    """Handle confirmation of scheduled meeting"""
    # Check for positive confirmation words/phrases
    positive_words = ["yes", "confirm", "sounds good", "perfect", "absolutely", "definitely", "sure", "ok", "okay", "great", "excellent"]
    
    utterance_lower = utterance.lower()
    has_positive = any(word in utterance_lower for word in positive_words)
    
    # Check for negative words/phrases
    negative_words = ["no", "cancel", "not interested", "remove", "stop", "don't", "won't"]
    has_negative = any(word in utterance_lower for word in negative_words)
    
    if has_positive and not has_negative:
        # Confirm the meeting
        return _confirm_meeting(state)
    else:
        reply = "No problem! Let me know if you'd like to reschedule or if you have any questions."
        return {
            "reply": reply,
            "tool_calls": [],
            "final": True
        }


def _handle_unknown(state: SessionState, utterance: str) -> Dict[str, Any]:
    """Handle unknown responses"""
    reply = "I want to make sure I understand correctly. Are you interested in learning more about our AI sales agent, or would you prefer I call you back at a different time?"
    return {
        "reply": reply,
        "tool_calls": [],
        "final": False
    }


def _schedule_demo_meeting(state: SessionState) -> Dict[str, Any]:
    """Schedule a demo meeting (for interested users)"""
    return _schedule_meeting_with_type(state, "demo")

def _schedule_meeting_with_type(state: SessionState, meeting_type: str) -> Dict[str, Any]:
    """Schedule a meeting with appropriate title and description"""
    parsed_dt_str = state.slots.get("parsed_datetime")
    
    if not parsed_dt_str:
        # No specific time provided, ask for clarification
        if meeting_type == "demo":
            reply = "Great! I'd love to schedule a demo call. When would work best for you? Please let me know a specific day and time, like 'Tomorrow at 2pm' or 'Next Tuesday at 10am'."
        else:
            reply = "Perfect! When would you like me to call you back? Please let me know a specific day and time, like 'Next Tuesday at 2pm' or 'Friday morning'."
        return {
            "reply": reply,
            "tool_calls": [],
            "final": False
        }
    
    try:
        parsed_dt = datetime.fromisoformat(parsed_dt_str)
    except (ValueError, TypeError) as e:
        # Invalid datetime format, ask for clarification
        reply = "I want to make sure I get the right time. Could you please specify a concrete time? For example, 'Tuesday at 2:00 PM' or 'Tomorrow morning at 10am'?"
        return {
            "reply": reply,
            "tool_calls": [],
            "final": False
        }
    
    # Set appropriate title and description based on meeting type
    if meeting_type == "demo":
        summary = f"AI Sales Agent Demo - {state.lead.name if state.lead else 'Prospect'}"
        description = "Demo call for AI sales agent service"
        reply = f"Perfect! I'll schedule a demo call for {parsed_dt.strftime('%A, %B %d at %I:%M %p')}. Does that work for you?"
        meta_type = "demo_call"
        # Mark that we're waiting for confirmation
        state.slots["confirmation"] = True
        final = False
    else:
        summary = f"Sales Follow-up Call - {state.lead.name if state.lead else 'Prospect'}"
        description = "Follow-up call for AI sales agent service"
        reply = f"Got it! I'll call you back on {parsed_dt.strftime('%A, %B %d at %I:%M %p')}. Thank you for your time!"
        meta_type = "follow_up_call"
        final = True
    
    # Create calendar event and log meeting request
    tool_calls = [
        ToolCall(
            name="calendar.create_event",
            args={
                "summary": summary,
                "description": description,
                "start_dt": parsed_dt.isoformat(),
                "end_dt": (parsed_dt + timedelta(minutes=30)).isoformat(),
                "attendees": [(state.lead.name, state.lead.email)] if state.lead else [],
                "calendar_id": "primary"
            }
        ),
        ToolCall(
            name="crm_stub.log_followup",
            args={
                "lead": state.lead.dict() if state.lead else {},
                "when": parsed_dt.isoformat(),
                "meta": {"type": meta_type}
            }
        )
    ]
    
    return {
        "reply": reply,
        "tool_calls": tool_calls,
        "final": final
    }

def _schedule_followup(state: SessionState) -> Dict[str, Any]:
    """Schedule a follow-up call (for busy users)"""
    return _schedule_meeting_with_type(state, "followup")


def _confirm_meeting(state: SessionState) -> Dict[str, Any]:
    """Confirm the scheduled meeting"""
    reply = "Excellent! I've confirmed your demo call. You'll receive a calendar invitation shortly. I'm looking forward to showing you how our AI sales agent can help your team close more deals!"
    
    return {
        "reply": reply,
        "tool_calls": [],
        "final": True
    }
