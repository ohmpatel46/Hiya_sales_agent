# Streamlit Voice Integration

## What Was Added

The Streamlit UI now supports voice output for agent responses.

### Features
1. **Voice Mode Toggle** - Checkbox next to user input to enable TTS
2. **Automatic Speech** - When enabled, agent responses are spoken automatically using OpenAI TTS
3. **Natural Speech** - Uses `tts_helpers` for natural pauses and phrasing

## How to Use

1. **Start a Call** - Click "📞 Simulate" next to a lead in the sidebar

2. **Enable Voice Mode** - Check the "🎤 Voice Mode" checkbox

3. **Type Responses** - Type your responses as normal

4. **Listen to Agent** - Agent replies will be spoken automatically using OpenAI's TTS API with the "nova" voice

## Technical Details

### Voice Output
- Uses `agent.voice_demo.speak_with_openai_tts()` 
- Voice: "nova" (friendly female voice)
- Natural mode: Enabled (adds strategic pauses)
- Requires: OpenAI API key in `.env`

### Dependencies
```bash
pip install openai pyaudio pygame
```

### Voice Mode
When enabled, the UI will:
1. Display agent response in chat
2. Automatically speak the response using OpenAI TTS
3. Use natural phrasing helpers for pauses

### Future Enhancements
- Voice input (STT) integration
- Push-to-talk button
- Voice recording component
- Multiple voice options in UI

## Configuration

Edit line 313 in `app/streamlit_ui.py` to change voice:
```python
speak_with_openai_tts(data['reply'], voice="nova", natural=True)
```

Available voices:
- `"nova"` - Female, friendly (default)
- `"shimmer"` - Female, warm
- `"alloy"` - Neutral
- `"echo"` - Male, professional
- `"fable"` - Male, expressive
- `"onyx"` - Male, authoritative

