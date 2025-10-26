# Frontend - Streamlit UI + FastAPI Backend

This directory contains the Streamlit frontend and FastAPI backend for the sales agent.

## Structure

```
frontend/
├── streamlit_app.py      # Main Streamlit UI (text-based)
├── pages/
│   └── voice_agent.py    # Voice-enabled Streamlit page
├── app/
│   ├── main.py          # FastAPI backend
│   └── deps.py          # Dependencies
└── README.md
```

## How to Run

From the project root:

```bash
# Start both FastAPI and Streamlit
python start.py
```

Or separately:

```bash
# FastAPI server
uvicorn frontend.app.main:app --reload

# Streamlit UI
streamlit run frontend/streamlit_app.py
```

## Features

### Streamlit UI (streamlit_app.py)
- Text-based conversation simulation
- Lead selection from Google Sheets
- Conversation history display
- Real-time chat interface

### Voice Agent Page (pages/voice_agent.py)
- Real-time voice conversation using OpenAI TTS/STT
- Voice Activity Detection (VAD) for continuous listening
- Configurable voice selection (nova, shimmer, alloy, echo, fable, onyx)
- 1.5x speed playback for faster responses
- Real leads from Google Sheets integration
- Calendar booking after meeting confirmation

### FastAPI Backend (app/main.py)
- `/trigger_call` - Start a conversation
- `/simulate` - Continue a conversation
- `/leads` - List all leads
- Vonage integration endpoints (for real calls)

## What It Uses

- **LangGraph workflow** from `agent/` for conversation orchestration
- **OpenAI API** for LLM (gpt-4o-mini)
- **OpenAI Whisper** for STT
- **OpenAI TTS** for voice output
- **Google Sheets API** for lead management
- **Google Calendar API** for meeting scheduling
- **Vonage API** for real phone calls (separate from LangGraph)

## Architecture

```
User → Streamlit UI → FastAPI (/trigger_call, /simulate) → LangGraph workflow
                                                           → LLM (OpenAI)
                                                           → Calendar Booking
                                                           → CRM Sheets
                                                           → Vonage (real calls)
```

## Notes

- The LangGraph workflow is shared with the terminal demos
- Vonage integration is separate and used for real phone calls
- All core logic is in the `agent/` directory
