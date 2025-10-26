# Final Repository Structure

## Complete Organization

```
Hiya_sales_agent/
├── agent/                          # Core agent logic (shared)
│   ├── simulated_agent/            # Simulated call agent
│   │   └── __init__.py            # (empty for now)
│   ├── real_call_agent/            # Real phone call agent
│   │   ├── vonage_calls.py        # Make Vonage calls
│   │   ├── vonage_service.py     # Vonage service logic
│   │   ├── vonage_webhook.py      # Webhook handlers
│   │   └── __init__.py
│   ├── tools/                      # Shared tools
│   │   ├── calendar.py            # Google Calendar
│   │   ├── crm_sheets.py          # Google Sheets
│   │   └── crm_stub.py            # CRM stub
│   └── [Core LangGraph files]     # Shared by both
│       ├── graph.py               # LangGraph orchestration
│       ├── state.py               # ConversationState
│       ├── llm_tools.py           # LLM integration
│       ├── planner.py             # Business logic
│       ├── response_node.py       # Response generation
│       ├── path_nodes.py          # Path handling
│       ├── schemas.py             # Pydantic models
│       ├── company_info.py        # Company info
│       ├── date_parser.py        # Date parsing
│       └── tts_helpers.py        # TTS helpers
│
├── terminal/                       # Terminal demos (MVP)
│   ├── demo.py                    # Text conversation
│   ├── voice_demo.py              # Voice (timeout)
│   ├── voice_demo_vad.py          # Voice (VAD)
│   └── README.md
│
├── frontend/                       # Frontend (Streamlit + FastAPI)
│   ├── streamlit_app.py           # Main Streamlit UI
│   ├── pages/
│   │   └── voice_agent.py        # Voice agent page
│   ├── app/
│   │   ├── main.py               # FastAPI endpoints
│   │   └── deps.py               # Dependencies
│   └── README.md
│
├── eval/                           # Evaluation files
│   ├── eval_sales_agent.py
│   ├── run_eval.py
│   ├── stories.json
│   ├── evaluation_log.jsonl
│   └── crm_log.jsonl
│
└── tests/                          # Unit tests
    ├── test_calendar_tool.py
    ├── test_google_calendar.py
    └── test_vonage_integration.py
```

## Directory Purposes

### Agent Structure

**Core Files (shared by all)**
- Used by both simulated and real call agents
- Contains LangGraph workflow, LLM integration, business logic

**`agent/simulated_agent/`**
- Code specific to simulated terminal demos
- Currently empty, ready for future terminal-specific code

**`agent/real_call_agent/`**
- Code for real phone calls via Vonage
- Vonage integration, webhook handlers, call management

**`agent/tools/`**
- Shared tools used by both simulated and real calls
- Google Calendar, Google Sheets, CRM integrations

### Usage

**Terminal Agent (MVP)**
```bash
python -m terminal.demo              # Text conversation
python -m terminal.voice_demo_vad    # Voice conversation (VAD)
```

**Frontend**
```bash
python start.py                      # Start both servers
```

### File Separation

- **Simulated calls**: Use `agent/graph.py` directly, no Vonage
- **Real calls**: Use `agent/real_call_agent/` for Vonage integration
- **Shared logic**: In `agent/` root (graph, state, llm_tools, etc.)

This separation makes it clear what code is for simulated demos vs real phone calls while keeping shared logic accessible to both.

