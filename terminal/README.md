# Terminal Agent Demos

This directory contains the MVP terminal-based sales agent demos.

## Files

- **demo.py**: Text-based conversation demo
- **voice_demo.py**: Voice demo with fixed-timeout recording
- **voice_demo_vad.py**: Voice demo with Voice Activity Detection (auto-stops on silence)

## How to Run

```bash
# Text demo
python -m terminal.demo

# Voice demo (basic)
python -m terminal.voice_demo

# Voice demo (with VAD)
python -m terminal.voice_demo_vad
```

## What They Use

All demos use the **LangGraph workflow** from `agent/`:
- `agent/graph.py` - Main LangGraph orchestration
- `agent/state.py` - ConversationState model
- `agent/llm_tools.py` - LLM helpers
- `agent/planner.py` - Deterministic business logic
- `agent/path_nodes.py` - Path nodes (includes calendar booking!)
- `agent/company_info.py` - Company information
- `agent/date_parser.py` - Date/time parsing
- `agent/tools/calendar.py` - Google Calendar integration
- `agent/tools/crm_sheets.py` - CRM Sheets integration

## Features

- Real calendar booking on meeting confirmation
- Real CRM integration with Google Sheets
- LLM-based intent classification and response generation
- Deterministic business logic (not LLM-driven)
- Tone adaptation
- Natural conversation flow

