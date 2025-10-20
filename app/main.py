from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uuid
from agent.schemas import Lead, SimulateInput, SimulateResponse, TriggerCallInput, TriggerCallResponse, VonageCallInput, VonageCallResponse
from agent.orchestrator import handle_turn, create_session
from agent.vonage_webhook import setup_vonage_routes
from agent.vonage_calls import make_vonage_call
from app.deps import get_settings
import os

app = FastAPI(title="Hiya Sales Agent", version="1.0.0")

# Enable CORS for localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory lead storage (for MVP)
leads: Dict[str, Lead] = {}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True, "status": "healthy"}


@app.post("/leads", response_model=Lead)
async def create_lead(lead_data: Dict[str, Any]):
    """Create a new lead"""
    try:
        # Generate unique ID
        lead_id = str(uuid.uuid4())
        
        # Create lead
        lead = Lead(
            id=lead_id,
            name=lead_data["name"],
            phone=lead_data["phone"],
            email=lead_data.get("email"),
            company=lead_data.get("company"),
            notes=lead_data.get("notes")
        )
        
        # Store lead
        leads[lead_id] = lead
        
        return lead
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/trigger_call", response_model=TriggerCallResponse)
async def trigger_call(input_data: TriggerCallInput):
    """Start a simulated call with a lead"""
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create session
        session = create_session(session_id, input_data.lead)
        
        # Get initial agent response (empty user input triggers greeting)
        response = handle_turn(session_id, input_data.lead, "")
        
        return TriggerCallResponse(
            session_id=session_id,
            reply=response["reply"],
            state=response["state"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulate", response_model=SimulateResponse)
async def simulate_conversation(input_data: SimulateInput):
    """Continue a simulated conversation"""
    try:
        # Handle the conversation turn
        response = handle_turn(input_data.session_id, input_data.lead, input_data.utterance)
        
        return SimulateResponse(
            reply=response["reply"],
            state=response["state"],
            tool_results=response["tool_results"],
            final=response["final"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str):
    """Get a lead by ID"""
    if lead_id not in leads:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return leads[lead_id]


@app.get("/leads")
async def list_leads():
    """List all leads"""
    return list(leads.values())


@app.post("/vonage/call", response_model=VonageCallResponse)
async def make_vonage_call_endpoint(input_data: VonageCallInput):
    """Make an actual Vonage phone call to a lead"""
    try:
        # Get webhook URL from environment or use provided one
        webhook_url = input_data.webhook_url or os.getenv('VONAGE_WEBHOOK_BASE_URL')
        
        if not webhook_url:
            return VonageCallResponse(
                call_uuid=None,
                success=False,
                message="Webhook URL not configured. Please set VONAGE_WEBHOOK_BASE_URL environment variable or provide webhook_url in request."
            )
        
        # Make the call
        call_uuid = make_vonage_call(input_data.lead, webhook_url)
        
        if call_uuid:
            return VonageCallResponse(
                call_uuid=call_uuid,
                success=True,
                message=f"Call initiated successfully to {input_data.lead.name} at {input_data.lead.phone}"
            )
        else:
            return VonageCallResponse(
                call_uuid=None,
                success=False,
                message="Failed to initiate call. Please check Vonage credentials and configuration."
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Setup Vonage webhook routes
setup_vonage_routes(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
