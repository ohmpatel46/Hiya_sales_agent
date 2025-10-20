from pydantic_settings import BaseSettings
from typing import Optional
import os
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle


class Settings(BaseSettings):
    app_env: str = "local"
    tz: str = "America/New_York"
    
    # Google Calendar
    google_credentials_path: str = "./google_credentials.json"
    google_calendar_id: str = "primary"
    google_sheets_spreadsheet_id: str | None = None
    
    # Model
    model_provider: str = "ollama"  # Changed from "stub" to "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"  # Use the available model
    openai_api_key: Optional[str] = None
    
    # Vonage
    vonage_api_key: Optional[str] = None
    vonage_api_secret: Optional[str] = None
    vonage_application_id: Optional[str] = None
    vonage_private_key_path: Optional[str] = None
    vonage_phone_number: Optional[str] = None
    vonage_webhook_base_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_calendar_service():
    """Get Google Calendar service client using OAuth"""
    settings = get_settings()
    
    if not os.path.exists(settings.google_credentials_path):
        return None
    
    # OAuth token file path
    token_file = settings.google_credentials_path.replace('.json', '_token.pickle')
    
    try:
        credentials = None
        
        # Load existing token if available
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                credentials = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                # Start OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.google_credentials_path,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                credentials = flow.run_local_server(port=0)
            
            # Save credentials for next time
            with open(token_file, 'wb') as token:
                pickle.dump(credentials, token)
        
        service = build('calendar', 'v3', credentials=credentials)
        return service
        
    except Exception as e:
        print(f"Failed to initialize Google Calendar service: {e}")
        return None


def get_sheets_service():
    """Get Google Sheets service client using OAuth (same creds as calendar)."""
    settings = get_settings()
    if not os.path.exists(settings.google_credentials_path):
        return None
    token_file = settings.google_credentials_path.replace('.json', '_token.pickle')
    try:
        credentials = None
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                credentials = pickle.load(token)
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.google_credentials_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                credentials = flow.run_local_server(port=0)
            with open(token_file, 'wb') as token:
                pickle.dump(credentials, token)
        return build('sheets', 'v4', credentials=credentials)
    except Exception as e:
        print(f"Failed to initialize Google Sheets service: {e}")
        return None
