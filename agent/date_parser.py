#!/usr/bin/env python3
"""
Enhanced date parsing for sales conversations
"""

from datetime import datetime, timedelta
import re
import dateparser


def parse_sales_date(text: str) -> str:
    """
    Parse date/time expressions commonly used in sales conversations
    Returns ISO datetime string or None
    """
    from datetime import datetime
    
    now = datetime.now()
    text_lower = text.lower().strip()
    
    # Handle specific patterns
    patterns = [
        # Tomorrow
        (r'tomorrow\s*(?:at\s*)?(\d{1,2}):?(\d{2})?\s*(am|pm)?', lambda m: _parse_tomorrow(m, now)),
        (r'tomorrow\s*(morning|afternoon|evening)', lambda m: _parse_tomorrow_period(m, now)),
        
        # Next week
        (r'next\s+week\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*(?:at\s*)?(\d{1,2}):?(\d{2})?\s*(am|pm)?', 
         lambda m: _parse_next_week_day(m, now)),
        (r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*(?:at\s*)?(\d{1,2}):?(\d{2})?\s*(am|pm)?', 
         lambda m: _parse_next_day(m, now)),
        
        # This week
        (r'this\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*(?:at\s*)?(\d{1,2}):?(\d{2})?\s*(am|pm)?', 
         lambda m: _parse_this_week_day(m, now)),
        
        # Day of week only
        (r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*(?:at\s*)?(\d{1,2}):?(\d{2})?\s*(am|pm)?', 
         lambda m: _parse_day_of_week(m, now)),
        (r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*(morning|afternoon|evening)', 
         lambda m: _parse_day_period(m, now)),
    ]
    
    for pattern, handler in patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                result = handler(match)
                if result:
                    return result.isoformat()
            except Exception as e:
                print(f"Error parsing pattern {pattern}: {e}")
                continue
    
    # Fallback to dateparser
    try:
        parsed = dateparser.parse(text, settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': now,
            'TIMEZONE': 'UTC'
        })
        if parsed:
            return parsed.isoformat()
    except Exception as e:
        print(f"Dateparser fallback error: {e}")
    
    return None


def _parse_tomorrow(match, now):
    """Parse tomorrow with optional time"""
    hour = 9  # default morning
    minute = 0
    
    if match.group(1):  # hour specified
        hour = int(match.group(1))
        if match.group(2):  # minute specified
            minute = int(match.group(2))
        if match.group(3):  # am/pm specified
            if match.group(3) == 'pm' and hour != 12:
                hour += 12
            elif match.group(3) == 'am' and hour == 12:
                hour = 0
    
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _parse_tomorrow_period(match, now):
    """Parse tomorrow with period (morning/afternoon/evening)"""
    period = match.group(1)
    tomorrow = now + timedelta(days=1)
    
    if period == 'morning':
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    elif period == 'afternoon':
        return tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
    elif period == 'evening':
        return tomorrow.replace(hour=18, minute=0, second=0, microsecond=0)
    
    return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)


def _parse_next_week_day(match, now):
    """Parse next week day with optional time"""
    day_name = match.group(1)
    hour = 9  # default morning
    minute = 0
    
    if len(match.groups()) > 1 and match.group(2):  # hour specified
        hour = int(match.group(2))
        if len(match.groups()) > 2 and match.group(3):  # minute specified
            minute = int(match.group(3))
        if len(match.groups()) > 3 and match.group(4):  # am/pm specified
            if match.group(4) == 'pm' and hour != 12:
                hour += 12
            elif match.group(4) == 'am' and hour == 12:
                hour = 0
    
    # Find next week's day (always next week, not this week)
    days_ahead = _get_days_ahead(day_name, now)
    target_date = now + timedelta(days=days_ahead)
    
    # Always move to next week for "next week" expressions
    target_date += timedelta(days=7)
    
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _parse_next_day(match, now):
    """Parse next day (not necessarily next week) with optional time"""
    day_name = match.group(1)
    hour = 9  # default morning
    minute = 0
    
    if len(match.groups()) > 1 and match.group(2):  # hour specified
        hour = int(match.group(2))
        if len(match.groups()) > 2 and match.group(3):  # minute specified
            minute = int(match.group(3))
        if len(match.groups()) > 3 and match.group(4):  # am/pm specified
            if match.group(4) == 'pm' and hour != 12:
                hour += 12
            elif match.group(4) == 'am' and hour == 12:
                hour = 0
    
    # Find next occurrence of the day
    days_ahead = _get_days_ahead(day_name, now)
    target_date = now + timedelta(days=days_ahead)
    
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _parse_this_week_day(match, now):
    """Parse this week day with optional time"""
    day_name = match.group(1)
    hour = 9  # default morning
    minute = 0
    
    if len(match.groups()) > 1 and match.group(2):  # hour specified
        hour = int(match.group(2))
        if len(match.groups()) > 2 and match.group(3):  # minute specified
            minute = int(match.group(3))
        if len(match.groups()) > 3 and match.group(4):  # am/pm specified
            if match.group(4) == 'pm' and hour != 12:
                hour += 12
            elif match.group(4) == 'am' and hour == 12:
                hour = 0
    
    # Find this week's day
    days_ahead = _get_days_ahead(day_name, now)
    target_date = now + timedelta(days=days_ahead)
    
    # If the day has already passed this week, move to next week
    if target_date <= now:
        target_date += timedelta(days=7)
    
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _parse_day_of_week(match, now):
    """Parse day of week (closest upcoming) with optional time"""
    day_name = match.group(1)
    hour = 9  # default morning
    minute = 0
    
    if len(match.groups()) > 1 and match.group(2):  # hour specified
        hour = int(match.group(2))
        if len(match.groups()) > 2 and match.group(3):  # minute specified
            minute = int(match.group(3))
        if len(match.groups()) > 3 and match.group(4):  # am/pm specified
            if match.group(4) == 'pm' and hour != 12:
                hour += 12
            elif match.group(4) == 'am' and hour == 12:
                hour = 0
    
    # Find closest upcoming day
    days_ahead = _get_days_ahead(day_name, now)
    target_date = now + timedelta(days=days_ahead)
    
    # If the day has already passed this week, move to next week
    if target_date <= now:
        target_date += timedelta(days=7)
    
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _parse_day_period(match, now):
    """Parse day with period (morning/afternoon/evening)"""
    day_name = match.group(1)
    period = match.group(2)
    
    # Find closest upcoming day
    days_ahead = _get_days_ahead(day_name, now)
    target_date = now + timedelta(days=days_ahead)
    
    # If the day has already passed this week, move to next week
    if target_date <= now:
        target_date += timedelta(days=7)
    
    if period == 'morning':
        return target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    elif period == 'afternoon':
        return target_date.replace(hour=14, minute=0, second=0, microsecond=0)
    elif period == 'evening':
        return target_date.replace(hour=18, minute=0, second=0, microsecond=0)
    
    return target_date.replace(hour=9, minute=0, second=0, microsecond=0)


def _get_days_ahead(day_name, now):
    """Get number of days ahead for a given day name"""
    days = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    target_day = days[day_name.lower()]
    current_day = now.weekday()  # Monday is 0, Sunday is 6
    
    days_ahead = target_day - current_day
    if days_ahead <= 0:
        days_ahead += 7
    
    return days_ahead


# Test the function
if __name__ == "__main__":
    test_cases = [
        "tomorrow at 2pm",
        "next week tuesday at 10am", 
        "this friday at 3pm",
        "next monday morning",
        "tuesday afternoon"
    ]
    
    print("Testing Enhanced Date Parsing")
    print("=" * 50)
    print(f"Today is: {datetime.now().strftime('%A, %B %d, %Y')}")
    print()
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"{i}. Testing: '{test_input}'")
        result = parse_sales_date(test_input)
        if result:
            dt = datetime.fromisoformat(result)
            print(f"   Parsed: {dt.strftime('%A, %B %d, %Y at %I:%M %p')}")
        else:
            print(f"   Parsed: None")
        print()
