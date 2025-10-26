# Hiya Sales Agent - AI Voice Sales Agent MVP

**Best Performance:** The terminal-based agent with Voice Activity Detection (`python -m terminal.voice_demo_vad`) is the most performant, production-ready version with full LangGraph workflow, OpenAI integration, Google Calendar booking, and CRM logging.

## Quick Start (MVP)

### Run the Voice Agent (Recommended)

```bash
# Voice conversation with Voice Activity Detection (auto-stops on silence)
python -m terminal.voice_demo_vad
```

**Features:**
- Real-time voice conversation using OpenAI Whisper (STT) and OpenAI TTS
- Voice Activity Detection for natural pauses
- Real calendar booking when meeting is confirmed
- Real CRM logging to Google Sheets
- LLM-based intent classification and response generation
- 1.5x speed playback for faster responses

### Text-Only Demo

```bash
# Text-based conversation
python -m terminal.demo
```

## Prerequisites

```bash
pip install -r requirements.txt
```

Create `.env` file:
```env
OPENAI_API_KEY=your_key_here
GOOGLE_CREDENTIALS_PATH=./google_credentials.json
GOOGLE_CALENDAR_ID=primary
TZ=America/New_York
```

## Repository Structure

### MVP Dependencies (Terminal Agent)

```
terminal/
├── voice_demo_vad.py       # Voice agent with VAD (MVP - RECOMMENDED)
├── voice_demo.py           # Voice agent with timeout
└── demo.py                 # Text-only agent

agent/                       # Shared core logic
├── graph.py                 # LangGraph state machine
├── state.py                 # ConversationState model
├── llm_tools.py            # OpenAI LLM integration
├── planner.py              # Business logic (deterministic)
├── response_node.py        # Response generation
├── path_nodes.py           # Path handlers (includes calendar!)
├── tools/
│   ├── calendar.py        # Google Calendar booking
│   ├── crm_sheets.py      # Google Sheets CRM
│   └── crm_stub.py        # Local CRM logging
```

**Shared by all:** All terminal demos use the shared `agent/` workflow.

### Frontend Dependencies (Streamlit App)

```
frontend/
├── streamlit_app.py        # Streamlit UI
├── pages/
│   └── voice_agent.py     # Voice-enabled Streamlit page
└── app/
    └── main.py            # FastAPI backend
```

### Key Differences

- **MVP (`terminal/`)**: Standalone, uses `agent/` directly for LangGraph workflow
- **Frontend (`frontend/`)**: Uses FastAPI to call LangGraph workflow, adds Streamlit UI layer

## Agent Workflow: LangGraph + LangChain

### State Machine (LangGraph)

The agent uses **LangGraph** to orchestrate conversation flow:

**State Model (`agent/state.py`):**
```python
class ConversationState:
    phase: str              # Current phase (intro, propose_meeting, etc.)
    intent: str             # User intent (interested, busy, question)
    tone: str               # User tone (friendly, rushed, skeptical)
    lead: Lead              # Lead information
    slots: dict             # Extracted data (datetime, etc.)
    done: bool              # Conversation complete?
    conversation_history: list  # Full conversation history
```

**Graph Nodes (`agent/graph.py`):**
1. `bridge_and_nudge` - Classifies intent/tone, generates response
2. `route_next_action` - Decides next action (deterministic Python)
3. Path nodes - Handle specific actions (scheduling, sending info, etc.)

**Deterministic Logic (`agent/planner.py`):**
- **Intent Classification**: Uses OpenAI to classify user intent
- **Tone Detection**: Heuristics + LLM for detecting user mood
- **DateTime Extraction**: Python regex to extract "tomorrow 2pm", etc.
- **Next Action Decision**: Python code (not LLM) decides what to do next

### LLM Integration (LangChain)

**OpenAI GPT-4o-mini** is used for:

1. **Intent Classification** (`agent/llm_tools.py`):
   - Takes user utterance and conversation history
   - Returns: `{"intent": "interested", "confidence": 0.9}`
   - Context-aware with conversation history

2. **Response Generation** (`agent/llm_tools.py`):
   - Takes state, utterance, and next action
   - Uses system prompt with:
     - Conversation history (last 2 turns)
     - Company info
     - Tone guide
     - Call-to-action
   - Returns natural, SDR-like responses

**System Prompt Structure:**
```python
You're an SDR for Autopitch AI talking to {lead.name}.

Context: {conversation_history[-2:]}
Goal: {next_action}  # propose_meeting, answer_question, etc.
Tone: {detected_tone}
CTA: Suggest a quick walkthrough call

Requirements:
- No meta-commentary
- Stay conversational
- Match user's tone
```

### Tools Integration

**Calendar Booking (`agent/tools/calendar.py`):**
```python
# When meeting confirmed in schedule_path_node
result = calendar.create_event(
    summary=f"Demo Call - {lead.name}",
    start_dt=datetime.isoformat(),
    end_dt=end_datetime.isoformat(),
    attendees=[(lead.name, lead.email)]
)
```

**CRM Logging (`agent/tools/crm_stub.py`):**
- Logs to `eval/crm_log.jsonl`
- Tracks outcomes, follow-ups, notes

**Google Sheets CRM (`agent/tools/crm_sheets.py`):**
- Lists leads from Google Sheets
- Upserts lead data
- Logs conversation outcomes

### Conversation Flow Example

```
User: "whos this?"
  ↓
LLM classifies intent: "question"
  ↓
LLM detects tone: "curious"
  ↓
Planner: provide_info (intro explanation)
  ↓
LLM generates: "Hi {name}, this is your AI sales agent..."
  ↓
Agent speaks via OpenAI TTS
  ↓
User: "tell me more"
  ↓
LLM classifies: "interested"
  ↓
Planner: provide_more_info
  ↓
LLM generates: "We help automate..." + CTA
  ↓
User: "tomorrow at 2pm works"
  ↓
Planner: confirm_meeting
  ↓
Extract datetime: tomorrow 2pm
  ↓
Calendar booking triggers
  ↓
Agent confirms + ends conversation
```

## Terminal Agent Features

### Voice Demo with VAD (`terminal/voice_demo_vad.py`)

**Real-time Voice:**
- **STT**: OpenAI Whisper transcribes speech
- **TTS**: OpenAI TTS speaks responses (onyx voice, 1.5x speed)
- **VAD**: WebRTC Voice Activity Detection auto-stops on silence
- **Continuous**: Automatically listens after agent speaks

**Smart Conversation:**
- Maintains full conversation history for context
- Adapts tone based on user mood
- Extracts datetime from natural language
- Books calendar events automatically

**CRM Integration:**
- Logs all conversations to Google Sheets
- Tracks meeting confirmations
- Records outcomes for analytics

### Text Demo (`terminal/demo.py`)

- Same LangGraph workflow
- Text input/output instead of voice
- Faster for testing/development

## Frontend App Features

### Streamlit UI (`frontend/streamlit_app.py`)

**Lead Management:**
- Add leads via sidebar form
- Integrates with Google Sheets if configured
- Lists existing leads from Sheets or local storage

**Call Simulation:**
- Text-based conversation interface
- Conversation history display
- Real-time agent responses
- Calendar event creation tracking

**API Integration:**
- Calls FastAPI endpoints
- Maintains session state
- Displays tool results

### Voice Agent Page (`frontend/pages/voice_agent.py`)

**Real-time Voice:**
- Voice input with VAD
- OpenAI TTS output
- Configurable voice selection
- 1.5x speed playback

**Lead Selection:**
- Loads leads from Google Sheets
- Demo lead option
- Real leads with phone/email

**Calendar Integration:**
- Books meetings after confirmation
- Shows event links

### FastAPI Backend (`frontend/app/main.py`)

**Endpoints:**
- `POST /trigger_call` - Start conversation
- `POST /simulate` - Continue conversation
- `GET /leads` - List leads
- `POST /leads` - Add lead

**LangGraph Integration:**
- Uses `agent/graph.py` for workflow
- Maintains session state in memory
- Returns conversation results

## Configuration

### Google Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project
3. Enable Google Calendar API
4. Create Service Account → Download JSON → Save as `google_credentials.json`
5. Share your calendar with the service account email

### Google Sheets Setup (Optional)

1. Create a Google Sheet
2. Create tabs: "Leads", "Calls", "Bookings"
3. Share with service account email
4. Add sheet ID to `.env`:
```env
GOOGLE_SHEETS_ID=your_sheet_id
```

### OpenAI Setup

1. Get API key from [OpenAI Platform](https://platform.openai.com/)
2. Add to `.env`:
```env
OPENAI_API_KEY=sk-...
```

### Running the MVP

```bash
# Voice agent (recommended)
python -m terminal.voice_demo_vad

# Text agent
python -m terminal.demo
```

### Running Frontend

```bash
# Start both FastAPI and Streamlit
python start.py

# Or separately:
uvicorn frontend.app.main:app --reload
streamlit run frontend/streamlit_app.py
```

## Architecture Summary

- **LangGraph**: State machine orchestration (deterministic business logic)
- **LangChain**: LLM integration (intent classification, response generation)
- **OpenAI**: GPT-4o-mini (LLM), Whisper (STT), TTS (voice)
- **Python**: Business decisions, datetime extraction, path routing
- **Tools**: Google Calendar, Google Sheets, CRM logging

## Development

### Adding a New Intent

1. Add intent in `agent/llm_tools.py` → `classify_intent_chain()`
2. Add action in `agent/planner.py` → `decide_next_action()`
3. Add response in `agent/llm_tools.py` → `generate_reply_chain()`
4. Add path node in `agent/path_nodes.py` if needed
5. Update graph in `agent/graph.py`

### Testing

```bash
# Run voice agent
python -m terminal.voice_demo_vad

# Run text agent
python -m terminal.demo
```

## Notes

- **Deterministic Logic**: Business decisions are Python-driven, not LLM-driven
- **LLM for Phrasing**: OpenAI is only used for natural responses and tone adaptation
- **Calendar Booking**: Happens automatically when meeting confirmed
- **CRM Logging**: All conversations logged to `eval/crm_log.jsonl`
- **Voice Demo**: Most natural conversation experience with VAD
