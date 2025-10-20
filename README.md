# Hiya Sales Agent MVP

## Overview

This is a local simulation of an AI voice agent that can place initial sales calls, pitch products, and schedule follow-up calls. The MVP focuses on text-based simulation with Google Calendar integration for scheduling.

## Features

- **Simulated Sales Call Flow**: AI agent conducts sales conversations with intent recognition
- **Google Calendar Integration**: Automatically schedules demo calls and follow-ups
- **Lead Management**: Add and manage prospects through a Streamlit UI
- **Evaluation Harness**: Test different conversation scenarios
- **Pluggable LLM Adapter**: Currently stubbed, ready for OpenAI integration
- **CRM Logging**: Tracks all interactions in JSON format

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Copy the sample environment file and configure it:

```bash
cp .env.sample .env
```

Edit `.env` with your settings:

```env
# General
APP_ENV=local
TZ=America/New_York

# Google Calendar
GOOGLE_CREDENTIALS_PATH=./google_credentials.json
GOOGLE_CALENDAR_ID=primary

# Model (stub now, swap later)
MODEL_PROVIDER=stub
OPENAI_API_KEY=
```

### 3. Set Up Google Calendar (Optional)

To enable calendar integration:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Download the JSON credentials file
   - Save as `google_credentials.json` in the project root
5. Share your calendar with the service account email

### 4. Test the Installation

Run the component test to verify everything is working:

```bash
python test_components.py
```

### 5. Run the Application

**Option 1: Use the startup script (recommended):**
```bash
python start.py
```

**Option 2: Manual startup:**
```bash
# Terminal 1 - Start FastAPI server
uvicorn app.main:app --reload

# Terminal 2 - Start Streamlit UI  
streamlit run app/streamlit_ui.py
```

The Streamlit UI will be available at `http://localhost:8501`

### 6. Try the Demo

Run a quick demo to see the system in action:

```bash
python demo.py
```

## Usage

### Streamlit UI

1. **Add a Lead**: Fill out the form in the sidebar with prospect information
2. **Start Call**: Click "Start Call" next to a lead to begin simulation
3. **Respond**: Type your responses to simulate the conversation
4. **Schedule**: The agent will attempt to schedule meetings in Google Calendar

**Example Responses:**
- `"Yes, I'm interested. Tomorrow at 2pm works"`
- `"I'm busy right now, call me next week"`
- `"Send me more information"`
- `"Not interested, please remove me"`

### API Endpoints

- `GET /health` - Health check
- `POST /leads` - Create a new lead
- `POST /trigger_call` - Start a simulated call
- `POST /simulate` - Continue a simulated conversation
- `GET /leads` - List all leads
- `GET /leads/{lead_id}` - Get specific lead

### Example API Usage

```python
import requests

# Create a lead
lead_data = {
    "name": "John Doe",
    "phone": "+1-555-123-4567",
    "email": "john@company.com",
    "company": "Acme Corp"
}
response = requests.post("http://localhost:8000/leads", json=lead_data)
lead = response.json()

# Start a call
response = requests.post("http://localhost:8000/trigger_call", json={"lead": lead})
call_data = response.json()
print(f"Agent: {call_data['reply']}")

# Continue conversation
response = requests.post("http://localhost:8000/simulate", json={
    "session_id": call_data["session_id"],
    "lead": lead,
    "utterance": "Yes, I'm interested. Tomorrow at 2pm works"
})
print(f"Agent: {response.json()['reply']}")
```

## Testing

### Run Unit Tests

```bash
pytest tests/
```

### Run Evaluation Harness

```bash
python eval/run_eval.py
```

The evaluation harness tests different conversation scenarios:
- Interested users who schedule demos
- Busy users who request follow-ups
- Users who request information
- Users who reject the offer

## Architecture

### Core Components

- **Orchestrator** (`agent/orchestrator.py`): Manages conversation state and tool execution
- **Sales Flow** (`agent/flows/sales.py`): Contains conversation logic and responses
- **NLU** (`agent/nlu.py`): Intent recognition and slot extraction
- **Calendar Tool** (`agent/tools/calendar.py`): Google Calendar integration
- **CRM Stub** (`agent/tools/crm_stub.py`): Logs interactions to JSON file

### Data Flow

1. User input → NLU parsing → Intent + Slots
2. Sales flow determines response → Tool calls
3. Tools execute (calendar, CRM) → Results
4. Response returned to user

### State Management

Sessions are stored in memory with:
- Lead information
- Conversation history
- Extracted slots (time, preferences)
- Tool execution results

## Configuration

### Environment Variables

- `APP_ENV`: Application environment (default: "local")
- `TZ`: Timezone for calendar events (default: "America/New_York")
- `GOOGLE_CREDENTIALS_PATH`: Path to Google service account JSON
- `GOOGLE_CALENDAR_ID`: Calendar ID (default: "primary")
- `MODEL_PROVIDER`: LLM provider (default: "stub")
- `OPENAI_API_KEY`: OpenAI API key (for future use)

### Calendar Integration

The system uses Google Calendar API with service account authentication. Events are created with:
- 30-minute duration for demo calls
- Email and popup reminders
- Attendee information when available

## Troubleshooting

### Common Issues

**Calendar events not created:**
- Check that `google_credentials.json` exists and is valid
- Verify the service account has calendar access
- Ensure the calendar ID is correct

**Streamlit UI not loading:**
- Make sure FastAPI server is running on port 8000
- Check that all dependencies are installed

**Tests failing:**
- Run `pytest -v` for detailed output
- Check that test data is valid

### Logs

- CRM interactions are logged to `crm_log.jsonl`
- FastAPI logs are displayed in the terminal
- Streamlit logs are shown in the browser console

## Next Steps

### Planned Enhancements

1. **Real LLM Integration**: Replace stub with OpenAI GPT models
2. **Voice TTS**: Add ElevenLabs text-to-speech
3. **Real Telephony**: Integrate Twilio for actual phone calls
4. **Enhanced Objection Handling**: More sophisticated response logic
5. **ISP Cancellation Flow**: Alternative conversation flows
6. **Analytics Dashboard**: Track conversion rates and metrics

### Development

To contribute:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the evaluation harness
5. Submit a pull request

## License

This project is for demonstration purposes. Please ensure compliance with applicable laws and regulations when using for actual sales calls.
