#!/usr/bin/env python3
"""
Comprehensive test script for Vonage integration
"""
import os
import sys
import json
import time
from typing import Optional
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.schemas import Lead
from agent.vonage_service import get_vonage_service
from agent.vonage_calls import make_vonage_call, get_call_status, hangup_call
from agent.vonage_webhook import get_webhook_handler

# Load environment variables
load_dotenv()


def test_vonage_credentials():
    """Test if Vonage credentials are properly configured"""
    print("Testing Vonage Credentials")
    print("=" * 40)
    
    required_vars = [
        'VONAGE_API_KEY',
        'VONAGE_API_SECRET', 
        'VONAGE_APPLICATION_ID',
        'VONAGE_PRIVATE_KEY_PATH',
        'VONAGE_PHONE_NUMBER',
        'VONAGE_WEBHOOK_BASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mask sensitive values
            if 'SECRET' in var or 'KEY' in var:
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
                print(f"[OK] {var}: {masked_value}")
            else:
                print(f"[OK] {var}: {value}")
    
    if missing_vars:
        print(f"\n[ERROR] Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("\n[SUCCESS] All Vonage credentials are configured!")
    return True


def test_vonage_service_initialization():
    """Test Vonage service initialization"""
    print("\nTesting Vonage Service Initialization")
    print("=" * 40)
    
    try:
        vonage_service = get_vonage_service()
        
        if vonage_service.client:
            print("[SUCCESS] Vonage service initialized successfully!")
            print(f"Application ID: {vonage_service.application_id}")
            return True
        else:
            print("[ERROR] Vonage service failed to initialize")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error initializing Vonage service: {e}")
        return False


def test_ncco_generation():
    """Test NCCO (Nexmo Call Control Object) generation"""
    print("\nTesting NCCO Generation")
    print("=" * 40)
    
    try:
        vonage_service = get_vonage_service()
        
        # Test basic NCCO generation
        ncco = vonage_service.generate_ncco("Hello, this is a test message.")
        print("[SUCCESS] Basic NCCO generated:")
        print(json.dumps(ncco, indent=2))
        
        # Test NCCO with input gathering
        webhook_url = os.getenv('VONAGE_WEBHOOK_BASE_URL')
        ncco_with_input = vonage_service.generate_ncco(
            "Hello, please say something.", 
            gather=True, 
            webhook_url=webhook_url
        )
        print("\n[SUCCESS] NCCO with input gathering:")
        print(json.dumps(ncco_with_input, indent=2))
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error generating NCCO: {e}")
        return False


def test_webhook_handler():
    """Test webhook handler initialization"""
    print("\nTesting Webhook Handler")
    print("=" * 40)
    
    try:
        handler = get_webhook_handler()
        print("[SUCCESS] Webhook handler initialized successfully!")
        print(f"Webhook base URL: {handler.webhook_base_url}")
        print(f"Active calls: {len(handler.active_calls)}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error initializing webhook handler: {e}")
        return False


def test_call_simulation():
    """Test call simulation without actually making a call"""
    print("\nTesting Call Simulation")
    print("=" * 40)
    
    try:
        # Create a test lead
        test_lead = Lead(
            id="test_vonage_call",
            name="Test User",
            phone="+1-555-123-4567",  # Test number - won't actually call
            email="test@example.com",
            company="Test Corp"
        )
        
        print(f"Test lead: {test_lead.name} ({test_lead.phone})")
        
        # Test webhook handler with simulated incoming call
        handler = get_webhook_handler()
        webhook_url = os.getenv('VONAGE_WEBHOOK_BASE_URL')
        
        # Simulate incoming call
        ncco = handler.handle_incoming_call("test-uuid-123", test_lead.phone, "+1-555-000-0000")
        print("Simulated incoming call NCCO:")
        print(json.dumps(ncco, indent=2))
        
        # Simulate user response
        response_ncco = handler.handle_user_response("test-uuid-123", "Hello, I'm interested in your service")
        print("\nSimulated user response NCCO:")
        print(json.dumps(response_ncco, indent=2))
        
        return True
        
    except Exception as e:
        print(f"Error in call simulation: {e}")
        return False


def test_actual_call(test_phone_number: Optional[str] = None):
    """Test making an actual call (requires real phone number)"""
    print("\nTesting Actual Call")
    print("=" * 40)
    
    if not test_phone_number:
        print("No test phone number provided. Skipping actual call test.")
        print("To test actual calls, run: python test_vonage_integration.py --call +1234567890")
        return True
    
    try:
        # Create a test lead with real phone number
        test_lead = Lead(
            id="actual_call_test",
            name="Test User",
            phone=test_phone_number,
            email="test@example.com",
            company="Test Corp"
        )
        
        webhook_url = os.getenv('VONAGE_WEBHOOK_BASE_URL')
        
        print(f"Making call to: {test_lead.name} ({test_lead.phone})")
        print(f"Webhook URL: {webhook_url}")
        
        # Make the call
        call_uuid = make_vonage_call(test_lead, webhook_url)
        
        if call_uuid:
            print(f"Call initiated successfully!")
            print(f"Call UUID: {call_uuid}")
            
            # Wait a bit and check call status
            print("Waiting 5 seconds before checking call status...")
            time.sleep(5)
            
            status = get_call_status(call_uuid)
            if status:
                print(f"Call status: {status}")
            
            # Note: Don't hang up automatically in test - let user decide
            print("Call is active. Use hangup_call() function to end it if needed.")
            
            return True
        else:
            print("Failed to initiate call")
            return False
            
    except Exception as e:
        print(f"Error making actual call: {e}")
        return False


def main():
    """Run all Vonage integration tests"""
    print("Vonage Integration Test Suite")
    print("=" * 50)
    
    # Check if we should make an actual call
    test_phone = None
    if len(sys.argv) > 1 and sys.argv[1] == "--call" and len(sys.argv) > 2:
        test_phone = sys.argv[2]
    
    tests = [
        ("Credentials", test_vonage_credentials),
        ("Service Initialization", test_vonage_service_initialization),
        ("NCCO Generation", test_ncco_generation),
        ("Webhook Handler", test_webhook_handler),
        ("Call Simulation", test_call_simulation),
        ("Actual Call", lambda: test_actual_call(test_phone))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"{test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\nAll tests passed! Vonage integration is ready.")
    else:
        print("\nSome tests failed. Please check the configuration and try again.")
    
    # Instructions
    print("\n" + "=" * 50)
    print("NEXT STEPS")
    print("=" * 50)
    print("1. Set up your Vonage account and get credentials")
    print("2. Configure environment variables in .env file")
    print("3. Set up ngrok for webhook handling:")
    print("   - Install ngrok: https://ngrok.com/")
    print("   - Run: ngrok http 8000")
    print("   - Update VONAGE_WEBHOOK_BASE_URL with your ngrok URL")
    print("4. Test with a real phone number:")
    print("   python test_vonage_integration.py --call +1234567890")
    print("5. Use the API endpoint /vonage/call to make calls from your application")


if __name__ == "__main__":
    main()
