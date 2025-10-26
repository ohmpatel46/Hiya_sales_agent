from typing import Dict, Any, Optional
from datetime import datetime
try:
    from frontend.app.deps import get_settings, get_sheets_service
except ImportError:
    # Fallback for standalone usage
    from typing import Optional, Any
    def get_settings():
        class Settings:
            google_credentials_path: Optional[str] = None
            google_sheets_id: str = None
        return Settings()
    def get_sheets_service():
        return None


LEADS_SHEET = "Leads"
CALLS_SHEET = "Calls"
BOOKINGS_SHEET = "Bookings"


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def ensure_sheets_exist() -> bool:
    settings = get_settings()
    if not settings.google_sheets_spreadsheet_id:
        return False
    service = get_sheets_service()
    if not service:
        return False
    try:
        ssid = settings.google_sheets_spreadsheet_id
        # Try reading metadata (will raise if not accessible)
        service.spreadsheets().get(spreadsheetId=ssid).execute()
        # Create headers if empty (best-effort; ignore errors)
        _init_sheet(service, ssid, LEADS_SHEET, [
            ["timestamp","phone","name","email","company","notes","last_intent","last_call_time","booking_time","calendar_event_id"]
        ])
        _init_sheet(service, ssid, CALLS_SHEET, [
            ["timestamp","call_uuid","phone","snippet","intent"]
        ])
        _init_sheet(service, ssid, BOOKINGS_SHEET, [
            ["timestamp","call_uuid","phone","start","end","event_id","htmlLink"]
        ])
        return True
    except Exception:
        return False


def _init_sheet(service, ssid: str, title: str, header_rows: list[list[str]]):
    try:
        # Check if data exists
        resp = service.spreadsheets().values().get(
            spreadsheetId=ssid, range=f"{title}!A1:A1"
        ).execute()
        values = resp.get("values")
        if not values:
            service.spreadsheets().values().update(
                spreadsheetId=ssid,
                range=f"{title}!A1",
                valueInputOption="RAW",
                body={"values": header_rows}
            ).execute()
    except Exception:
        # Sheet might not exist; create it
        try:
            service.spreadsheets().batchUpdate(
                spreadsheetId=ssid,
                body={"requests":[{"addSheet":{"properties":{"title": title}}}]}
            ).execute()
            service.spreadsheets().values().update(
                spreadsheetId=ssid,
                range=f"{title}!A1",
                valueInputOption="RAW",
                body={"values": header_rows}
            ).execute()
        except Exception:
            pass


def upsert_lead(phone: str, name: Optional[str]=None, email: Optional[str]=None, company: Optional[str]=None, notes: Optional[str]=None) -> Dict[str, Any]:
    settings = get_settings()
    ssid = settings.google_sheets_spreadsheet_id
    service = get_sheets_service()
    if not ssid or not service:
        return {"ok": False, "error": "Sheets not configured"}
    try:
        # Append new row (simple upsert for POC)
        safe_phone = f"'{phone}" if phone else ""
        row = [[_now_iso(), safe_phone, name or "", email or "", company or "", notes or "", "", "", "", ""]]
        service.spreadsheets().values().append(
            spreadsheetId=ssid,
            range=f"{LEADS_SHEET}!A:Z",
            valueInputOption="RAW",
            body={"values": row}
        ).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def log_call_event(call_uuid: str, phone: str, snippet: str, intent: Optional[str]=None) -> Dict[str, Any]:
    settings = get_settings()
    ssid = settings.google_sheets_spreadsheet_id
    service = get_sheets_service()
    if not ssid or not service:
        return {"ok": False, "error": "Sheets not configured"}
    try:
        safe_phone = f"'{phone}" if phone else ""
        row = [[_now_iso(), call_uuid, safe_phone, snippet, intent or ""]]
        service.spreadsheets().values().append(
            spreadsheetId=ssid,
            range=f"{CALLS_SHEET}!A:Z",
            valueInputOption="RAW",
            body={"values": row}
        ).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def record_booking(call_uuid: str, phone: str, start_iso: str, end_iso: str, event_id: str, html_link: str) -> Dict[str, Any]:
    settings = get_settings()
    ssid = settings.google_sheets_spreadsheet_id
    service = get_sheets_service()
    if not ssid or not service:
        return {"ok": False, "error": "Sheets not configured"}
    try:
        safe_phone = f"'{phone}" if phone else ""
        row = [[_now_iso(), call_uuid, safe_phone, start_iso, end_iso, event_id, html_link]]
        service.spreadsheets().values().append(
            spreadsheetId=ssid,
            range=f"{BOOKINGS_SHEET}!A:Z",
            valueInputOption="RAW",
            body={"values": row}
        ).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_leads(limit: int = 50) -> Dict[str, Any]:
    """Return latest leads as a list of dicts (best-effort)."""
    settings = get_settings()
    ssid = settings.google_sheets_spreadsheet_id
    service = get_sheets_service()
    if not ssid or not service:
        return {"ok": False, "error": "Sheets not configured", "leads": []}
    try:
        resp = service.spreadsheets().values().get(
            spreadsheetId=ssid,
            range=f"{LEADS_SHEET}!A2:J"
        ).execute()
        rows = resp.get("values", [])
        # Map to dicts using known header order
        keys = ["timestamp","phone","name","email","company","notes","last_intent","last_call_time","booking_time","calendar_event_id"]
        items = []
        for row in rows[-limit:]:
            obj = {k: (row[i] if i < len(row) else "") for i, k in enumerate(keys)}
            items.append(obj)
        return {"ok": True, "leads": items}
    except Exception as e:
        return {"ok": False, "error": str(e), "leads": []}


def lead_exists(phone: str) -> bool:
    """Check if a lead with this phone exists in Sheets (best-effort)."""
    settings = get_settings()
    ssid = settings.google_sheets_spreadsheet_id
    service = get_sheets_service()
    if not ssid or not service:
        return False
    try:
        resp = service.spreadsheets().values().get(
            spreadsheetId=ssid,
            range=f"{LEADS_SHEET}!B2:B"
        ).execute()
        rows = resp.get("values", [])
        phones = {r[0] for r in rows if r}
        return phone in phones
    except Exception:
        return False


