#!/usr/bin/env python3
"""
Vonage Voice Call Integration
"""
from agent.schemas import Lead
from agent.vonage_service import get_vonage_service
from typing import Optional


def make_vonage_call(lead: Lead, webhook_base_url: str = "https://your-ngrok-url.ngrok.io") -> Optional[str]:
    """
    Make a Vonage voice call to a lead
    
    Args:
        lead: Lead to call
        webhook_base_url: Base URL for webhooks (use ngrok for local development)
    
    Returns:
        Call UUID if successful, None if failed
    """
    vonage = get_vonage_service()
    
    if not vonage.client:
        print("Vonage client not initialized. Please check your credentials.")
        return None
    
    # Make the call
    call_uuid = vonage.make_call(lead, webhook_base_url)
    
    if call_uuid:
        print(f"Call initiated successfully!")
        print(f"Call UUID: {call_uuid}")
        print(f"Calling: {lead.name} at {lead.phone}")
        print(f"Webhook URL: {webhook_base_url}")
        return call_uuid
    else:
        print("Failed to initiate call")
        return None


def get_call_status(call_uuid: str) -> Optional[dict]:
    """Get status of a Vonage call"""
    vonage = get_vonage_service()
    return vonage.get_call_status(call_uuid)


def hangup_call(call_uuid: str) -> bool:
    """Hang up a Vonage call"""
    vonage = get_vonage_service()
    return vonage.hangup_call(call_uuid)


if __name__ == "__main__":
    # Test Vonage call functionality
    print("Testing Vonage Call Integration")
    print("=" * 40)
    
    # Create a test lead
    test_lead = Lead(
        id="vonage_test",
        name="Test User",
        phone="+1-555-123-4567",  # Replace with real number for testing
        email="test@example.com",
        company="Test Corp"
    )
    
    print(f"Test lead: {test_lead.name} ({test_lead.phone})")
    print("\nNote: Replace the phone number with a real number to test actual calling.")
    print("Also, make sure to set up ngrok for webhook handling.")
    
    # Test Vonage service initialization
    vonage = get_vonage_service()
    if vonage.client:
        print("\nVonage service initialized successfully!")
        print(f"Application ID: {vonage.application_id}")
    else:
        print("\nVonage service not initialized. Check your credentials.")
