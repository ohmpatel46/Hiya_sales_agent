"""
Deterministic planner logic - decides business strategy without LLM.

CRITICAL: This is deterministic Python logic, not LLM reasoning.
The LLM is only responsible for phrasing. This code decides what
to do next (propose_meeting, reschedule, ask_channel_pref, etc.)

This gives us complete control over conversation flow and makes the
agent auditable and compliant.
"""

from agent.state import ConversationState
from typing import Optional
from datetime import datetime
import dateparser
import re


def extract_datetime(user_utterance: str, state: ConversationState) -> None:
    """
    Extract date and time into separate slots, then combine into datetime.
    
    Steps:
    1. Extract date keyword (e.g., "today", "tomorrow") → fills date_slot
    2. Extract time keyword (e.g., "6pm", "morning") → fills time_slot
    3. If both slots filled, combine and parse → fills datetime
    """
    print(f"[DEBUG] extract_datetime called with: '{user_utterance}'")
    user_lower = user_utterance.lower()
    
    # Extract time part FIRST - check for times like "4:15pm", "6pm", "11am" anywhere in utterance
    exact_time_match = re.search(r'\b(\d{1,2}):?(\d{2})?\s*(pm|am)\b', user_lower)
    if exact_time_match:
        # Reconstruct the full time string
        hour = exact_time_match.group(1)
        minute = exact_time_match.group(2)
        ampm = exact_time_match.group(3)
        
        if minute:
            time_text = f"{hour}:{minute}{ampm}"
        else:
            time_text = f"{hour}{ampm}"
        
        state.slots["time_slot"] = time_text
        print(f"[DEBUG] Filled time_slot with exact time: '{state.slots['time_slot']}' (hour={hour}, minute={minute})")
    
    # Extract core date keywords (today, tomorrow, next week, etc.)
    # Look for the core date word in the utterance
    core_date_keywords = ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    date_slot_filled = False
    for keyword in core_date_keywords:
        if keyword in user_lower:
            state.slots["date_slot"] = keyword
            print(f"[DEBUG] Filled date_slot: '{keyword}'")
            date_slot_filled = True
            break
    
    # Also check for week-based patterns
    if not date_slot_filled:
        if "next week" in user_lower:
            state.slots["date_slot"] = "next week"
            print(f"[DEBUG] Filled date_slot: 'next week'")
            date_slot_filled = True
        elif "this week" in user_lower:
            state.slots["date_slot"] = "this week"
            print(f"[DEBUG] Filled date_slot: 'this week'")
            date_slot_filled = True
    
    # Check for vague time descriptors (morning, evening, etc.) - these DON'T fill time_slot
    # but we can use them to suggest a specific time later
    vague_time_patterns = {
        r'\bmorning\b': 'morning',
        r'\bafternoon\b': 'afternoon', 
        r'\bevening\b': 'evening',
        r'\bafter work\b': 'after work'
    }
    
    for pattern, descriptor in vague_time_patterns.items():
        if re.search(pattern, user_lower) and not state.slots.get("time_slot"):
            print(f"[DEBUG] Detected vague time descriptor: '{descriptor}' (will suggest specific time)")
            break
    
    # If we have both date_slot and time_slot, combine and parse immediately
    if state.slots.get("date_slot") and state.slots.get("time_slot"):
        date_part = state.slots["date_slot"]
        time_part = state.slots["time_slot"]
        
        # date_slot is already a core keyword like "today", "tomorrow", etc.
        # Combine for parsing: "today 6pm", "tomorrow 2pm", etc.
        combined = f"{date_part} {time_part}"
        print(f"[DEBUG] Both slots filled! Combining '{date_part}' + '{time_part}' → '{combined}'")
        
        # Try to parse the combined datetime
        try:
            from agent.date_parser import parse_sales_date
            parsed_str = parse_sales_date(combined)
            if parsed_str:
                dt = datetime.fromisoformat(parsed_str)
                state.slots["datetime"] = dt
                print(f"[DEBUG] Parsed combined datetime: {dt}")
                return
        except Exception as e:
            print(f"[DEBUG] Error parsing combined: {e}")
    
    # If we still don't have datetime, check if we should suggest a time
    # If we have date_slot but not time_slot, suggest a specific time
    if state.slots.get("date_slot") and not state.slots.get("time_slot") and not state.slots.get("datetime"):
        date_slot = state.slots["date_slot"]
        state.slots["suggested_time"] = suggest_specific_time_from_slot(date_slot)
        print(f"[DEBUG] Have date but no time, suggesting: {state.slots['suggested_time']}")


def suggest_specific_time_from_slot(date_slot: str) -> str:
    """
    Given a date slot like "today" or "tomorrow", suggest a specific time.
    """
    date_lower = date_slot.lower()
    
    # Capitalize day names for display
    day_capitalized = date_slot.capitalize() if len(date_slot) > 2 else date_slot.title()
    
    if date_lower == "today":
        return "later today at 4pm"
    elif date_lower == "tomorrow":
        return "tomorrow at 2pm"
    elif "next week" in date_lower:
        return "next Tuesday at 2pm"
    elif date_lower in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        return f"{day_capitalized} at 2pm"
    else:
        return "tomorrow at 2pm"


def suggest_specific_time(reference: str, days_offset: Optional[int]) -> str:
    """
    Suggest a specific time when user gives vague reference like "tomorrow" or "next week".
    
    Returns a string like "tomorrow at 2pm" or "next Tuesday at 2pm"
    """
    from datetime import timedelta
    reference_lower = reference.lower()
    
    # Handle special cases for "today" variations
    if "today" in reference_lower or days_offset == 0:
        # Same day - suggest afternoon/evening
        if "morning" in reference_lower:
            return "today at 10am"
        elif "afternoon" in reference_lower:
            return "today at 2pm"
        elif "evening" in reference_lower:
            return "today at 6pm"
        else:
            return "later today at 4pm"
    
    if days_offset is None:
        # Day of week - find next occurrence
        days_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, 
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }
        days_offset = days_map.get(reference.lower(), 1)
    
    target_date = datetime.now() + timedelta(days=days_offset)
    
    # Suggest 2pm as default time
    return target_date.strftime("%A at 2pm")


def decide_next_action(state: ConversationState) -> str:
    """
    Decide what goal we're pushing toward next based on intent and state.
    
    Allowed next_action values:
      - "propose_meeting" - ask for a demo slot
      - "reschedule" - ask for callback time
      - "ask_channel_pref" - ask email vs SMS preference
      - "clarify_time" - get more specific time
      - "propose_specific_time" - suggest a specific time (e.g., "tomorrow at 2pm?")
      - "graceful_exit" - politely end the call
      - "ask_for_clarification" - ask what they want
    
    Rules:
    - if state.intent == "interested": next_action = "propose_meeting"
    - if state.intent == "busy": next_action = "reschedule"
    - if state.intent == "send_info": next_action = "ask_channel_pref"
    - if state.intent == "not_interested": next_action = "graceful_exit"
    - if state.intent == "question": next_action = "propose_meeting"
    - if state.intent == "unclear": next_action = "ask_for_clarification"
    
    Edge cases:
    - if user gave vague time with suggested_time, propose that specific time
    - if user gave vague time without suggested_time, clarify the time
    """
    
    print(f"[DEBUG] Planning next action for intent: {state.intent}, phase: {state.phase}")
    print(f"[DEBUG] Slots: date_slot={state.slots.get('date_slot')}, time_slot={state.slots.get('time_slot')}, datetime={state.slots.get('datetime')}")
    
    # PRIORITY 1: If we have a concrete datetime, we should confirm it
    if state.slots.get("datetime") and not state.slots.get("confirmation"):
        print(f"[DEBUG] Have datetime but no confirmation yet - confirm meeting")
        return "confirm_meeting"
    
    # PRIORITY 2: Have both date_slot and time_slot, but no datetime yet → should have parsed, confirm anyway
    if state.slots.get("date_slot") and state.slots.get("time_slot") and not state.slots.get("datetime"):
        print(f"[DEBUG] Have both date_slot and time_slot, confirm meeting")
        return "confirm_meeting"
    
    # PRIORITY 3: Have date_slot but not time_slot → propose specific time
    if state.slots.get("date_slot") and not state.slots.get("time_slot"):
        print(f"[DEBUG] Have date_slot but no time_slot - propose specific time")
        return "propose_specific_time"
    
    # PRIORITY 4: Have suggested_time → propose it
    if state.slots.get("suggested_time") and not state.slots.get("datetime"):
        print(f"[DEBUG] Have suggested_time - propose it")
        return "propose_specific_time"
    
    # Map intent to next_action deterministically
    # Check if we've already provided company info
    info_provided = state.slots.get("info_provided", False)
    
    # Check if this is an initial intro question (who is this, what is this about)
    user_lower = state.current_user_utterance.lower() if hasattr(state, 'current_user_utterance') and state.current_user_utterance else ""
    is_intro_question = any(phrase in user_lower for phrase in ["whos this", "who is this", "whats this", "what is this", "who's calling", "what's this about"])
    
    # Check if user is explicitly asking for a meeting or to send info
    explicit_meeting = any(phrase in user_lower for phrase in [
        "book a call", "schedule", "let's talk", "let me check my calendar", "set up",
        "we could", "sounds good", "let's do that", "sure let's", "that works"
    ])
    explicit_send_info = any(phrase in user_lower for phrase in ["send info", "send me information", "pdf", "email", "text me"])
    
    # Check if user is asking for more details (after initial info)
    is_asking_for_more = any(phrase in user_lower for phrase in ["tell me more", "more about", "more details", "learn more", "explain more", "interesting"])
    
    # Check if user explicitly wants to schedule (includes agreeing to a proposed call)
    explicit_scheduling = any(phrase in user_lower for phrase in ["we can do the call", "yeah we can", "sounds good", "lets do it", "yes lets", "lets schedule"])
    if explicit_scheduling:
        explicit_meeting = True  # Override with more explicit signal
        print(f"[DEBUG] Detected explicit scheduling agreement")
    
    print(f"[DEBUG] Routing decision: intent={state.intent}, info_provided={info_provided}, is_asking_for_more={is_asking_for_more}, explicit_meeting={explicit_meeting}, explicit_send_info={explicit_send_info}")
    
    intent_to_action = {
        "interested": "provide_info" if not info_provided else ("propose_meeting" if explicit_meeting else ("provide_more_info" if is_asking_for_more else "propose_meeting")),
        "busy": "reschedule",
        "send_info": "ask_channel_pref",
        "not_interested": "graceful_exit",
        "question": "provide_info" if (state.phase == "intro" and is_intro_question) else ("provide_more_info" if is_asking_for_more else ("answer_question" if info_provided else "provide_info")),
        "unclear": "provide_info" if (state.phase == "intro" and is_intro_question) else "ask_for_clarification"
    }
    
    intent = state.intent or "unclear"
    next_action = intent_to_action.get(intent, "ask_for_clarification")
    
    print(f"[DEBUG] Decided next action: {next_action}")
    
    return next_action


def should_confirm_meeting(state: ConversationState) -> bool:
    """
    Check if we should ask for confirmation before booking.
    
    Returns True if:
    - We have a concrete datetime
    - We haven't already asked for confirmation
    - We have a meeting type (demo or followup)
    """
    has_concrete_datetime = state.slots.get("datetime") is not None
    not_already_confirmed = "confirmation" not in state.slots
    has_meeting_type = "meeting_type" in state.slots
    
    return has_concrete_datetime and not_already_confirmed and has_meeting_type


def determine_meeting_type(intent: str, phase: str) -> str:
    """
    Determine meeting type based on intent and phase.
    
    Returns:
        "demo" - for interested users who want a product demo
        "followup" - for busy users who want a callback
    """
    if intent == "interested":
        return "demo"
    elif intent == "busy":
        return "followup"
    else:
        # Default based on context
        return "demo" if "meeting" in phase else "followup"

