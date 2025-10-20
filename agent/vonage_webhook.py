#!/usr/bin/env python3
"""
Vonage Webhook Handler for Voice Calls
"""
from fastapi import FastAPI, Request, Form
from fastapi.responses import Response
from agent.vonage_service import get_vonage_service
from agent.orchestrator import handle_turn
from agent.tools import calendar as calendar_tool
from agent.tools import crm_sheets
from agent.schemas import Lead
from typing import Dict, Any, Optional
import json
import os
import logging


class VonageWebhookHandler:
    """Handles Vonage webhook events for voice calls"""
    
    def __init__(self):
        self.vonage = get_vonage_service()
        self.active_calls: Dict[str, Dict[str, Any]] = {}  # call_uuid -> call_data
        self.webhook_base_url = os.getenv('VONAGE_WEBHOOK_BASE_URL', 'https://your-ngrok-url.ngrok.io')
    
    def handle_incoming_call(self, call_uuid: str, from_number: str, to_number: str) -> list:
        """
        Handle incoming call (when Vonage connects to our webhook)
        
        Args:
            call_uuid: Vonage call UUID
            from_number: Caller's phone number
            to_number: Our Vonage number
        
        Returns:
            NCCO response
        """
        print(f"DEBUG: handle_incoming_call called with UUID: {call_uuid}")
        
        # Create a lead from the call
        lead = Lead(
            id=f"call_{call_uuid}",
            name="Unknown Caller",
            phone=from_number,
            email=None,
            company=None
        )
        
        # Store call data
        self.active_calls[call_uuid] = {
            'lead': lead,
            'session_id': f"vonage_call_{call_uuid}",
            'turn_count': 0
        }
        
        print(f"DEBUG: Created lead: {lead.name} ({lead.phone})")
        # CRM upsert (best effort)
        try:
            crm_sheets.ensure_sheets_exist()
            crm_sheets.upsert_lead(phone=lead.phone, name=lead.name)
        except Exception as e:
            print(f"DEBUG: CRM upsert error: {e}")
        
        # Get initial agent response
        try:
            response = handle_turn(f"vonage_call_{call_uuid}", lead, "")
            print(f"DEBUG: Agent response: {response}")
        except Exception as e:
            print(f"DEBUG: Error in handle_turn: {e}")
            response = None
        
        if response and response.get("reply"):
            # Record any booking tool results
            for tr in response.get("tool_results", []):
                try:
                    if tr.get("created") and tr.get("id"):
                        crm_sheets.record_booking(
                            call_uuid=call_uuid,
                            phone=lead.phone,
                            start_iso=str(tr.get("start", "")),
                            end_iso="",
                            event_id=tr.get("id", ""),
                            html_link=tr.get("htmlLink", "")
                        )
                except Exception as e:
                    print(f"DEBUG: CRM booking log error: {e}")
            # Generate NCCO with initial greeting
            ncco = self.vonage.generate_ncco(response["reply"], gather=True, webhook_url=self.webhook_base_url)
            print(f"DEBUG: Generated NCCO: {ncco}")
            return ncco
        else:
            # Fallback message
            print(f"DEBUG: Using fallback message")
            ncco = self.vonage.generate_ncco(
                "Hello! Thank you for calling. I'm having technical difficulties. Please try again later.",
                gather=False
            )
            return ncco
    
    def handle_user_response(self, call_uuid: str, speech_result: str) -> list:
        """
        Handle user speech input
        
        Args:
            call_uuid: Vonage call UUID
            speech_result: Transcribed speech from user
        
        Returns:
            NCCO response
        """
        print(f"DEBUG: handle_user_response called with UUID: {call_uuid}")
        print(f"DEBUG: Active calls: {list(self.active_calls.keys())}")
        
        if call_uuid not in self.active_calls:
            print(f"DEBUG: Call UUID {call_uuid} not found in active calls!")
            return self.vonage.generate_ncco("I'm sorry, I lost track of our conversation. Goodbye!", gather=False)
        
        call_data = self.active_calls[call_uuid]
        lead = call_data['lead']
        session_id = call_data['session_id']
        
        # Process user input through sales flow
        response = handle_turn(session_id, lead, speech_result)
        
        if response and response.get("reply"):
            # Log call snippet to CRM
            try:
                crm_sheets.log_call_event(call_uuid, lead.phone, snippet=speech_result)
            except Exception as e:
                print(f"DEBUG: CRM call log error: {e}")
            # Check if conversation is done
            if response.get("final", False):
                # End the call
                call_data['turn_count'] += 1
                ncco = self.vonage.generate_ncco(response["reply"], gather=False)
                
                # Add hangup action
                ncco.append({"action": "hangup"})
                
                # Clean up call data
                del self.active_calls[call_uuid]
                
                return ncco
            else:
                # Record any booking tool results
                for tr in response.get("tool_results", []):
                    try:
                        if tr.get("created") and tr.get("id"):
                            crm_sheets.record_booking(
                                call_uuid=call_uuid,
                                phone=lead.phone,
                                start_iso=str(tr.get("start", "")),
                                end_iso="",
                                event_id=tr.get("id", ""),
                                html_link=tr.get("htmlLink", "")
                            )
                    except Exception as e:
                        print(f"DEBUG: CRM booking log error: {e}")
                # Continue conversation
                call_data['turn_count'] += 1
                ncco = self.vonage.generate_ncco(response["reply"], gather=True, webhook_url=self.webhook_base_url)
                return ncco
        else:
            # Error handling
            ncco = self.vonage.generate_ncco(
                "I'm sorry, I didn't understand that. Could you please repeat?",
                gather=True,
                webhook_url=self.webhook_base_url
            )
            return ncco
    
    def handle_call_status(self, call_uuid: str, status: str):
        """Handle call status updates"""
        print(f"Call {call_uuid} status: {status}")
        
        if status in ['completed', 'busy', 'no-answer', 'failed']:
            # Clean up call data
            if call_uuid in self.active_calls:
                del self.active_calls[call_uuid]
    
    def get_active_calls(self) -> Dict[str, Dict[str, Any]]:
        """Get all active calls"""
        return self.active_calls.copy()


# Global webhook handler
_webhook_handler: Optional[VonageWebhookHandler] = None


def get_webhook_handler() -> VonageWebhookHandler:
    """Get the global webhook handler"""
    global _webhook_handler
    if _webhook_handler is None:
        _webhook_handler = VonageWebhookHandler()
    return _webhook_handler


def setup_vonage_routes(app: FastAPI):
    """Setup Vonage webhook routes"""
    
    @app.post("/vonage/voice/input")
    async def handle_voice_input(request: Request):
        """Handle Vonage voice input webhook"""
        try:
            # Debug: Log the raw request
            print(f"DEBUG: Received webhook request")
            print(f"DEBUG: Content-Type: {request.headers.get('content-type')}")
            
            # Try to get JSON data instead of form data
            json_data = await request.json()
            print(f"DEBUG: JSON data keys: {list(json_data.keys())}")
            
            uuid = json_data.get("uuid")
            speech_data = json_data.get("speech")
            from_data = json_data.get("from")
            to_data = json_data.get("to")
            
            print(f"DEBUG: UUID: {uuid}")
            print(f"DEBUG: Speech data: {speech_data}")
            
            # Normalize phone numbers from payload (can be dict or string)
            def _extract_number(value):
                if isinstance(value, dict):
                    return value.get("number") or value.get("phone") or ""
                return str(value) if value is not None else ""
            from_number = _extract_number(from_data)
            to_number = _extract_number(to_data)
            print(f"DEBUG: From: {from_number} To: {to_number}")
            
            # Extract the best speech result
            speech_text = None
            if speech_data and isinstance(speech_data, dict) and "results" in speech_data:
                results = speech_data["results"]
                if results and len(results) > 0:
                    # Get the first (highest confidence) result
                    speech_text = results[0]["text"]
                    print(f"DEBUG: Extracted speech text: {speech_text}")
            
            handler = get_webhook_handler()
            
            # Ensure call context exists before handling speech (first webhook for some routes is speech)
            try:
                active = handler.get_active_calls()
                if uuid and uuid not in active:
                    print(f"DEBUG: Initializing call context for UUID: {uuid}")
                    # Initialize active call context (discard returned NCCO here)
                    handler.handle_incoming_call(uuid, from_number, to_number)
            except Exception as init_err:
                print(f"DEBUG: Error initializing call context: {init_err}")
            
            if speech_text:
                # User provided speech input
                print(f"DEBUG: Handling user response: {speech_text}")
                ncco = handler.handle_user_response(uuid, speech_text)
            else:
                # Initial call or no speech
                print(f"DEBUG: Handling incoming call")
                ncco = handler.handle_incoming_call(uuid, from_number, to_number)
            
            print(f"DEBUG: Returning NCCO: {ncco}")
            return Response(content=json.dumps(ncco), media_type="application/json")
            
        except Exception as e:
            print(f"DEBUG: Webhook error: {e}")
            # Return a simple NCCO to avoid hanging up
            fallback_ncco = [{"action": "talk", "text": "I'm sorry, there was a technical issue. Goodbye!", "voiceName": "Amy"}]
            return Response(content=json.dumps(fallback_ncco), media_type="application/json")
    
    @app.get("/vonage/voice/status")
    async def handle_status_webhook(
        uuid: str = None,
        status: str = None
    ):
        """Handle Vonage status webhook"""
        handler = get_webhook_handler()
        handler.handle_call_status(uuid, status)
        return {"status": "ok"}
    
    @app.get("/vonage/calls")
    async def get_active_calls():
        """Get active calls (for debugging)"""
        handler = get_webhook_handler()
        return {"active_calls": handler.get_active_calls()}
    
    @app.get("/vonage/voice/fallback")
    async def handle_fallback():
        """Handle fallback webhook (for errors)"""
        logger = logging.getLogger(__name__)
        logger.warning("Fallback webhook called - there may be an issue with the main webhook")
        return {"status": "fallback", "message": "Fallback webhook reached"}


if __name__ == "__main__":
    # Test webhook handler
    print("Testing Vonage Webhook Handler")
    print("=" * 40)
    
    handler = get_webhook_handler()
    print("Webhook handler initialized!")
    
    # Test NCCO generation
    test_ncco = handler.vonage.generate_ncco("Hello, this is a test.")
    print("\nTest NCCO:")
    print(json.dumps(test_ncco, indent=2))
