from typing import Dict, Any, Optional, Tuple
import re
import dateparser
from agent.schemas import Lead
from agent.llm import get_ollama_client
from app.deps import get_settings


def parse_intent(text: str) -> str:
    """Parse user intent from text using keyword matching"""
    text_lower = text.lower()
    
    # Intent keywords
    interested_keywords = ["interested", "sounds good", "ok let's talk", "book", "yes", "sure", "let's do it"]
    busy_keywords = ["busy", "later", "not now", "another time", "tomorrow", "next week", "call me later"]
    send_info_keywords = ["send info", "email me", "text me", "send the link", "more information"]
    reject_keywords = ["not interested", "no thanks", "remove me", "don't call", "not now"]
    schedule_keywords = ["schedule", "book", "appointment", "meeting", "call"]
    
    # Check for intent
    if any(keyword in text_lower for keyword in interested_keywords):
        return "interested"
    elif any(keyword in text_lower for keyword in busy_keywords):
        return "busy"
    elif any(keyword in text_lower for keyword in send_info_keywords):
        return "send_info"
    elif any(keyword in text_lower for keyword in reject_keywords):
        return "reject"
    elif any(keyword in text_lower for keyword in schedule_keywords):
        return "schedule_followup"
    else:
        return "unknown"


def extract_time_slots(text: str) -> Dict[str, Any]:
    """Extract time-related information from text"""
    slots = {}
    
    # Try to parse dates/times
    parsed_date = dateparser.parse(text, settings={'PREFER_DATES_FROM': 'future'})
    if parsed_date:
        slots['parsed_datetime'] = parsed_date.isoformat()
        slots['time_mentioned'] = True
    
    # Look for specific time patterns
    time_patterns = [
        r'(\d{1,2}):(\d{2})\s*(am|pm)?',
        r'(\d{1,2})\s*(am|pm)',
        r'(morning|afternoon|evening)',
        r'(tomorrow|today|next week|this week)',
    ]
    
    for pattern in time_patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            slots['time_pattern'] = matches[0]
            break
    
    return slots


def parse(text: str, lead: Optional[Lead] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Parse user utterance to extract intent and slots
    
    Returns:
        Tuple of (intent, slots)
    """
    settings = get_settings()
    
    # Try LLM parsing first if not using stub
    if settings.model_provider != "stub":
        try:
            llm_result = llm_parse(text, lead)
            if llm_result:
                intent, slots = llm_result
                # Add lead context to slots
                if lead:
                    slots['lead_name'] = lead.name
                    slots['lead_company'] = lead.company
                return intent, slots
        except Exception as e:
            print(f"LLM parsing failed, falling back to keyword matching: {e}")
    
    # Fallback to keyword-based parsing
    intent = parse_intent(text)
    slots = extract_time_slots(text)
    
    # Add any additional context from lead
    if lead:
        slots['lead_name'] = lead.name
        slots['lead_company'] = lead.company
    
    return intent, slots


def llm_parse(text: str, lead: Optional[Lead] = None) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Use Ollama to parse intent and extract slots
    """
    try:
        client = get_ollama_client()
        lead_dict = lead.dict() if lead else None
        result = client.parse_intent_and_slots(text, lead_dict)
        
        intent = result.get("intent", "unknown")
        slots = result.get("slots", {})
        
        return intent, slots
        
    except Exception as e:
        print(f"Ollama parsing error: {e}")
        return None
