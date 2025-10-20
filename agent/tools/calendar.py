from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import pytz
from app.deps import get_settings, get_calendar_service


def iso_localize(dt: datetime) -> datetime:
    """Convert datetime to timezone-aware ISO format"""
    settings = get_settings()
    tz = pytz.timezone(settings.tz)
    
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    else:
        dt = dt.astimezone(tz)
    
    return dt


def create_event(
    summary: str,
    description: str,
    start_dt: str,
    end_dt: str,
    attendees: List[Tuple[str, str]] = None,
    calendar_id: str = "primary"
) -> Dict[str, Any]:
    """
    Create a Google Calendar event
    
    Args:
        summary: Event title
        description: Event description
        start_dt: Start datetime (ISO string)
        end_dt: End datetime (ISO string)
        attendees: List of (name, email) tuples
        calendar_id: Calendar ID (default: "primary")
    
    Returns:
        Dict with event details or error info
    """
    service = get_calendar_service()
    if not service:
        return {
            "error": "Calendar service not available",
            "created": False
        }
    
    try:
        # Parse and localize datetimes
        start_datetime = iso_localize(datetime.fromisoformat(start_dt))
        end_datetime = iso_localize(datetime.fromisoformat(end_dt))
        
        # Prepare attendees
        attendee_list = []
        if attendees:
            for name, email in attendees:
                attendee_list.append({
                    "email": email,
                    "displayName": name
                })
        
        # Create event body
        event_body = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": get_settings().tz
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": get_settings().tz
            },
            "attendees": attendee_list,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},  # 1 day before
                    {"method": "popup", "minutes": 10}        # 10 minutes before
                ]
            }
        }
        
        # Create the event
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()
        
        return {
            "id": event["id"],
            "htmlLink": event.get("htmlLink", ""),
            "created": True,
            "summary": event["summary"],
            "start": event["start"]["dateTime"]
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "created": False
        }
