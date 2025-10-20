import requests
import json
from typing import Dict, Any, Optional, List
from app.deps import get_settings


class OllamaClient:
    """Client for interacting with Ollama API"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url
        self.model = self.settings.ollama_model
    
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate text using Ollama"""
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            if system:
                payload["system"] = system
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except Exception as e:
            print(f"Ollama API error: {e}")
            return ""
    
    def parse_intent_and_slots(self, text: str, lead: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Use Ollama to parse intent and extract slots"""
        
        from datetime import datetime
        import dateparser
        
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        
        # First, try to extract datetime using enhanced date parser
        parsed_datetime = None
        try:
            from agent.date_parser import parse_sales_date
            parsed_datetime = parse_sales_date(text)
        except Exception as e:
            print(f"Enhanced date parser error: {e}")
            # Fallback to dateparser
            try:
                parsed_dt = dateparser.parse(
                    text, 
                    settings={
                        'PREFER_DATES_FROM': 'future',
                        'RELATIVE_BASE': datetime.now(),
                        'PREFER_DAY_OF_MONTH': 'first',
                        'TIMEZONE': 'UTC'
                    }
                )
                if parsed_dt:
                    parsed_datetime = parsed_dt.isoformat()
            except Exception as e2:
                print(f"Dateparser fallback error: {e2}")
        
        system_prompt = f"""You are an expert at parsing sales conversation intents and extracting relevant information.

IMPORTANT: Today's date is {current_date}. 

Your task is to analyze user responses in sales calls and extract:
1. Intent: One of these categories
   - interested: User shows interest and wants to schedule a DEMO (not just a follow-up call)
     Examples: "yes", "sure", "I'm interested", "tell me more", "I want to learn more", "sounds good"
   - schedule_followup: User wants to schedule a follow-up call (not a demo)
     Examples: "call me back", "I'm busy now", "schedule a call"
   - busy: User is busy but might be interested later
   - send_info: User wants more information sent (documents, emails, materials)
     Examples: "send me information", "email me details", "I want materials"
   - reject: User explicitly rejects or wants to be removed
   - unknown: Cannot determine intent

Key distinction: "interested" = wants to see a demo/product presentation, "schedule_followup" = wants a phone call back

2. Slots: Extract relevant information like:
   - time_preference: General time preference (morning, afternoon, evening)
   - contact_preference: How they want to be contacted (email, phone, text)
   - reason: Reason for rejection or delay

NOTE: Do NOT try to parse dates/times - that's handled separately. Focus on intent and other slots.

Respond ONLY with valid JSON in this exact format:
{{
  "intent": "interested",
  "slots": {{
    "time_preference": "morning",
    "contact_preference": "email"
  }}
}}"""

        user_prompt = f"""Analyze this sales conversation response:

User said: "{text}"

Lead context: {lead or "No lead context"}

Extract the intent and relevant slots."""

        try:
            response = self.generate(user_prompt, system_prompt)
            
            # Try to parse JSON response
            if response.startswith('{') and response.endswith('}'):
                result = json.loads(response)
            else:
                # Fallback: try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = {"intent": "unknown", "slots": {}}
            
            # Add the parsed datetime from dateparser
            if parsed_datetime:
                result["slots"]["parsed_datetime"] = parsed_datetime
            
            return result
            
        except Exception as e:
            print(f"Error parsing with Ollama: {e}")
            # Return basic result with dateparser datetime if available
            result = {
                "intent": "unknown", 
                "slots": {}
            }
            if parsed_datetime:
                result["slots"]["parsed_datetime"] = parsed_datetime
            return result


# Global client instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
