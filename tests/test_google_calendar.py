#!/usr/bin/env python3
"""
Test Google Calendar integration
"""
import os
from datetime import datetime, timedelta
from app.deps import get_settings, get_calendar_service

def test_google_calendar():
    """Test Google Calendar API connection and event creation"""
    print("Testing Google Calendar Integration")
    print("=" * 50)
    
    try:
        # Check if credentials file exists
        settings = get_settings()
        creds_path = settings.google_credentials_path
        
        if not os.path.exists(creds_path):
            print(f"X Credentials file not found: {creds_path}")
            print("Please download google_credentials.json from Google Cloud Console")
            return False
        
        print(f"OK Credentials file found: {creds_path}")
        
        # Test calendar service
        print("Connecting to Google Calendar...")
        service = get_calendar_service()
        
        if not service:
            print("X Failed to create calendar service")
            return False
        
        print("OK Successfully connected to Google Calendar!")
        
        # Test creating a calendar event
        print("Testing event creation...")
        
        # Create a test event for tomorrow
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=30)
        
        event = {
            'summary': 'Test Event - Hiya Sales Agent',
            'description': 'This is a test event created by the Hiya Sales Agent',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/New_York',
            },
            'attendees': [
                {'email': 'test@example.com'},
            ],
        }
        
        # Create the event
        created_event = service.events().insert(
            calendarId=settings.google_calendar_id,
            body=event
        ).execute()
        
        print(f"OK Test event created successfully!")
        print(f"   Event ID: {created_event['id']}")
        print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M')}")
        
        # Clean up - delete the test event
        print("Cleaning up test event...")
        service.events().delete(
            calendarId=settings.google_calendar_id,
            eventId=created_event['id']
        ).execute()
        
        print("OK Test event deleted successfully!")
        print("\nSUCCESS: Google Calendar integration is working perfectly!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure google_credentials.json is in the project root")
        print("2. Check that Google Calendar API is enabled")
        print("3. Verify OAuth consent screen is configured")
        print("4. Make sure you're added as a test user")
        return False

if __name__ == "__main__":
    test_google_calendar()

