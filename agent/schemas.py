from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime


class Lead(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    notes: Optional[str] = None


class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any] = {}


class TraceTurn(BaseModel):
    ts: datetime = Field(default_factory=datetime.utcnow)
    user: Optional[str] = None
    agent: Optional[str] = None
    tool_calls: List[ToolCall] = []
    tool_results: List[Dict[str, Any]] = []
    state: Dict[str, Any] = {}


class SessionState(BaseModel):
    session_id: str
    lead: Optional[Lead] = None
    slots: Dict[str, Any] = {}   # e.g., {"time": "...", "date": "..."}
    history: List[TraceTurn] = []
    done: bool = False


class SimulateInput(BaseModel):
    session_id: str
    lead: Lead
    utterance: str


class TriggerCallInput(BaseModel):
    lead: Lead


class TriggerCallResponse(BaseModel):
    session_id: str
    reply: str
    state: Dict[str, Any]


class SimulateResponse(BaseModel):
    reply: str
    state: Dict[str, Any]
    tool_results: List[Dict[str, Any]] = []
    final: bool = False


class VonageCallInput(BaseModel):
    lead: Lead
    webhook_url: Optional[str] = None


class VonageCallResponse(BaseModel):
    call_uuid: Optional[str] = None
    success: bool
    message: str