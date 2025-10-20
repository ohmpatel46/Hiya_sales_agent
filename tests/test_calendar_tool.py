import pytest
import os
from datetime import datetime, timedelta
from agent.tools.calendar import create_event, iso_localize
from app.deps import get_settings


def test_iso_localize():
    """Test datetime localization"""
    dt = datetime(2024, 1, 15, 14, 30)
    localized = iso_localize(dt)
    
    assert localized.tzinfo is not None
    assert localized.year == 2024
    assert localized.month == 1
    assert localized.day == 15


def test_create_event_no_credentials():
    """Test calendar event creation without credentials (should fail gracefully)"""
    # Temporarily rename credentials file if it exists
    settings = get_settings()
    creds_path = settings.google_credentials_path
    temp_path = creds_path + ".backup"
    
    creds_exist = os.path.exists(creds_path)
    if creds_exist:
        os.rename(creds_path, temp_path)
    
    try:
        # Try to create event without credentials
        result = create_event(
            summary="Test Event",
            description="Test Description",
            start_dt=(datetime.now() + timedelta(hours=1)).isoformat(),
            end_dt=(datetime.now() + timedelta(hours=1, minutes=15)).isoformat(),
            attendees=[("Test User", "test@example.com")],
            calendar_id="primary"
        )
        
        assert not result.get("created", False)
        assert "error" in result or "not available" in str(result)
        
    finally:
        # Restore credentials file if it existed
        if creds_exist and os.path.exists(temp_path):
            os.rename(temp_path, creds_path)


@pytest.mark.skipif(
    not os.path.exists(get_settings().google_credentials_path),
    reason="Google Calendar credentials not found"
)
def test_create_event_with_credentials():
    """Test calendar event creation with credentials"""
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(minutes=15)
    
    result = create_event(
        summary="Test Event - Hiya Sales Agent",
        description="Test event created by Hiya Sales Agent",
        start_dt=start_time.isoformat(),
        end_dt=end_time.isoformat(),
        attendees=[("Test User", "test@example.com")],
        calendar_id="primary"
    )
    
    assert result.get("created", False), f"Event creation failed: {result}"
    assert "id" in result, "Event ID should be returned"
    assert "htmlLink" in result, "Event HTML link should be returned"
    
    # Clean up - delete the test event
    try:
        from app.deps import get_calendar_service
        service = get_calendar_service()
        if service:
            service.events().delete(
                calendarId="primary",
                eventId=result["id"]
            ).execute()
    except Exception:
        # Ignore cleanup errors
        pass


def test_create_event_invalid_datetime():
    """Test calendar event creation with invalid datetime"""
    result = create_event(
        summary="Test Event",
        description="Test Description",
        start_dt="invalid-datetime",
        end_dt="invalid-datetime",
        attendees=[],
        calendar_id="primary"
    )
    
    assert not result.get("created", False)
    assert "error" in result


def test_create_event_no_attendees():
    """Test calendar event creation without attendees"""
    start_time = datetime.now() + timedelta(hours=2)
    end_time = start_time + timedelta(minutes=15)
    
    result = create_event(
        summary="Test Event No Attendees",
        description="Test event without attendees",
        start_dt=start_time.isoformat(),
        end_dt=end_time.isoformat(),
        attendees=[],
        calendar_id="primary"
    )
    
    # Should work even without attendees
    if result.get("created", False):
        assert "id" in result
    else:
        # If it fails, it should be due to credentials, not attendees
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__])
