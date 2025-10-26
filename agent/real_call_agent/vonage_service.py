#!/usr/bin/env python3
"""
Vonage Voice Integration for Sales Agent
"""
import vonage
from typing import Optional, Dict, Any
import os
import json
import logging
from dotenv import load_dotenv
from agent.schemas import Lead

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VonageService:
    """Vonage voice service for making phone calls"""
    
    def __init__(self):
        self.client = None
        self.application_id = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Vonage client"""
        try:
            api_key = os.getenv('VONAGE_API_KEY')
            api_secret = os.getenv('VONAGE_API_SECRET')
            self.application_id = os.getenv('VONAGE_APPLICATION_ID')
            private_key_path = os.getenv('VONAGE_PRIVATE_KEY_PATH')
            
            if not all([api_key, api_secret, self.application_id]):
                logger.error("Vonage credentials not found in environment variables")
                logger.error("Required: VONAGE_API_KEY, VONAGE_API_SECRET, VONAGE_APPLICATION_ID")
                return
            
            if private_key_path and not os.path.exists(private_key_path):
                logger.error(f"Vonage private key file not found: {private_key_path}")
                return
            
            # Create auth object
            auth = vonage.Auth(
                api_key=api_key,
                api_secret=api_secret,
                application_id=self.application_id,
                private_key=private_key_path
            )
            
            # Initialize Vonage client
            self.client = vonage.Vonage(auth)
            
            logger.info("Vonage client initialized successfully!")
            logger.info(f"Application ID: {self.application_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vonage client: {e}")
            self.client = None
    
    def make_call(self, lead: Lead, webhook_url: str) -> Optional[str]:
        """
        Make a phone call to a lead using Vonage Voice API
        
        Args:
            lead: Lead to call
            webhook_url: URL to handle call events
        
        Returns:
            Call UUID if successful, None if failed
        """
        if not self.client:
            logger.error("Vonage client not initialized")
            return None
        
        if not webhook_url:
            logger.error("Webhook URL is required for making calls")
            return None
        
        logger.info(f"Making call to {lead.name} ({lead.phone})")
        
        try:
            # Create NCCO (Nexmo Call Control Object) for the call
            ncco = [
                {
                    "action": "talk",
                    "text": f"Hey {lead.name}, I am calling about TopSales, our AI-based lead generator that turns cold leads into warm ones using realistic automated calls and scheduling follow-ups. Would you like to learn more?",
                    "voiceName": "Joanna"
                },
                {
                    "action": "input",
                    "type": ["speech"],
                    "speech": {
                        "endOnSilence": 2.0,
                        "timeout": 5
                    },
                    "eventUrl": [f"{webhook_url}/vonage/voice/input"],
                    "eventMethod": "POST"
                }
            ]
            
            # Import required models
            from vonage_voice.models.requests import CreateCallRequest, ToPhone
            from vonage_voice.models.common import Phone
            
            # Clean phone number (remove + and any non-digits)
            clean_phone = ''.join(filter(str.isdigit, lead.phone))
            clean_from_phone = ''.join(filter(str.isdigit, os.getenv('VONAGE_PHONE_NUMBER', '')))
            
            # Create call request
            call_request = CreateCallRequest(
                to=[ToPhone(number=clean_phone)],
                from_=Phone(number=clean_from_phone),
                ncco=ncco
            )
            
            # Make the call
            response = self.client.voice.create_call(call_request)
            
            call_uuid = response.uuid
            logger.info(f"Call initiated successfully to {lead.name} ({lead.phone})")
            logger.info(f"Call UUID: {call_uuid}")
            return call_uuid
            
        except Exception as e:
            logger.error(f"Failed to make call to {lead.name}: {e}")
            return None
    
    def generate_ncco(self, message: str, gather: bool = True, webhook_url: str = None) -> list:
        """
        Generate NCCO (Nexmo Call Control Object) for voice response
        
        Args:
            message: Text to speak
            gather: Whether to gather user input
            webhook_url: URL for webhook events
        
        Returns:
            NCCO list
        """
        # Remove SSML tags and use plain text for better compatibility
        clean_message = message.replace('<speak>', '').replace('</speak>', '')
        clean_message = clean_message.replace('<prosody rate="fast">', '').replace('</prosody>', '')
        clean_message = clean_message.replace('<emphasis level="moderate">', '').replace('</emphasis>', '')
        clean_message = clean_message.replace('<break time="120ms"/>', ' ')
        
        ncco = [
            {
                "action": "talk",
                "text": clean_message,
                "voiceName": "Joanna"
            }
        ]
        
        if gather and webhook_url:
            ncco.append({
                "action": "input",
                "type": ["speech"],
                "speech": {
                    "endOnSilence": 2.0,
                    "timeout": 5
                },
                "eventUrl": [f"{webhook_url}/vonage/voice/input"],
                "eventMethod": "POST"
            })
        
        return ncco
    
    def get_call_status(self, call_uuid: str) -> Optional[Dict[str, Any]]:
        """Get call status"""
        if not self.client:
            return None
        
        try:
            call = self.client.voice.get_call(call_uuid)
            return {
                'uuid': call['uuid'],
                'status': call['status'],
                'direction': call['direction'],
                'from': call['from'],
                'to': call['to'],
                'start_time': call.get('start_time'),
                'end_time': call.get('end_time'),
                'duration': call.get('duration')
            }
        except Exception as e:
            logger.error(f"Failed to get call status: {e}")
            return None
    
    def hangup_call(self, call_uuid: str) -> bool:
        """Hang up a call"""
        if not self.client:
            return False
        
        try:
            self.client.voice.update_call(call_uuid, action='hangup')
            logger.info(f"Call {call_uuid} hung up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to hang up call {call_uuid}: {e}")
            return False


# Global Vonage service instance
_vonage_service: Optional[VonageService] = None


def get_vonage_service() -> VonageService:
    """Get the global Vonage service instance"""
    global _vonage_service
    if _vonage_service is None:
        _vonage_service = VonageService()
    return _vonage_service


def make_call(lead: Lead, webhook_url: str) -> Optional[str]:
    """Convenience function to make a call"""
    return get_vonage_service().make_call(lead, webhook_url)


def generate_ncco(message: str, gather: bool = True, webhook_url: str = None) -> list:
    """Convenience function to generate NCCO"""
    return get_vonage_service().generate_ncco(message, gather, webhook_url)


if __name__ == "__main__":
    # Test Vonage service
    print("Testing Vonage Service")
    print("=" * 30)
    
    vonage_service = get_vonage_service()
    
    if vonage_service.client:
        print("Vonage client initialized successfully!")
        print(f"Application ID: {vonage_service.application_id}")
        
        # Test NCCO generation
        ncco = vonage_service.generate_ncco("Hello, this is a test message.")
        print("\nGenerated NCCO:")
        print(json.dumps(ncco, indent=2))
    else:
        print("Vonage client not initialized. Check your credentials.")
