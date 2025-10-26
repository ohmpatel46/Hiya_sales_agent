"""
Voice-Enabled Sales Agent - Streamlit UI
Dedicated page for voice interactions
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import streamlit as st
import requests
import json
import tempfile
from typing import Dict, Any

# Add agent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Check for voice dependencies
try:
    from openai import OpenAI
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    st.warning("⚠️ Voice dependencies not installed. Run: pip install openai")

if VOICE_AVAILABLE:
    try:
        from agent.voice_demo import speak_with_openai_tts, transcribe_audio_with_whisper_api
    except ImportError:
        VOICE_AVAILABLE = False

# Check for VAD
try:
    import pyaudio
    import webrtcvad
    import wave
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    if VOICE_AVAILABLE:
        st.warning("⚠️ VAD dependencies not installed. Run: pip install pyaudio webrtcvad")


def record_with_vad_continuous():
    """
    Record audio with Voice Activity Detection - continuous listening mode.
    Returns transcribed text when user stops speaking.
    """
    if not VAD_AVAILABLE:
        return None
    
    try:
        p = pyaudio.PyAudio()
        
        # Audio format for VAD
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        FRAME_DURATION_MS = 30
        CHUNK = int(RATE * FRAME_DURATION_MS / 1000)  # 480 samples for 30ms at 16kHz
        
        vad = webrtcvad.Vad(2)  # Balanced sensitivity
        
        silence_frames = 0
        frames = []
        SILENCE_DURATION = 1.0
        speech_detected = False
        
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        # Record until silence detected
        recording = True
        while recording:
            chunk = stream.read(CHUNK, exception_on_overflow=False)
            
            try:
                is_speech = vad.is_speech(chunk, RATE)
                
                if is_speech:
                    silence_frames = 0
                    speech_detected = True
                else:
                    if speech_detected:
                        silence_frames += 1
                        silence_duration = (silence_frames * FRAME_DURATION_MS) / 1000.0
                        if silence_duration >= SILENCE_DURATION:
                            recording = False
                            break
                
                frames.append(chunk)
            except:
                frames.append(chunk)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        if not frames:
            return None
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
            
            wf = wave.open(temp_audio_path, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
        
        # Transcribe
        transcript = transcribe_audio_with_whisper_api(temp_audio_path)
        
        # Clean up
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        
        return transcript
        
    except Exception as e:
        st.error(f"Recording error: {e}")
        return None


def speak(text: str, voice: str = "nova") -> bool:
    """Speak text using OpenAI TTS"""
    if VOICE_AVAILABLE:
        try:
            return speak_with_openai_tts(text, voice=voice, natural=True)
        except Exception as e:
            st.error(f"TTS error: {e}")
            return False
    return False


def main():
    st.set_page_config(
        page_title="Voice Sales Agent",
        page_icon="🎤",
        layout="wide"
    )
    
    st.title("🎤 Voice-Enabled Sales Agent")
    st.markdown("Real-time voice conversation with AI sales agent")
    
    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'conversation_done' not in st.session_state:
        st.session_state.conversation_done = False
    if 'voice_mode' not in st.session_state:
        st.session_state.voice_mode = True  # Always on for voice page
    if 'selected_lead' not in st.session_state:
        st.session_state.selected_lead = None
    
    # Sidebar for lead selection
    with st.sidebar:
        st.header("Lead Selection")
        
        # Try to load leads from Google Sheets
        try:
            from agent.tools import crm_sheets
            if crm_sheets.ensure_sheets_exist():
                res = crm_sheets.list_leads(limit=20)
                if res.get("ok") and res.get("leads"):
                    # Radio button for lead selection
                    lead_options = {}
                    for lead in res["leads"][::-1]:
                        display = f"{lead.get('name') or 'Unknown'} - {lead.get('phone')}"
                        api_lead = {
                            "id": lead.get("phone", "sheet"),
                            "name": lead.get("name") or "Unknown",
                            "phone": lead.get("phone"),
                            "email": lead.get("email") or None,
                            "company": lead.get("company") or None,
                        }
                        lead_options[display] = api_lead
                    
                    # Add demo option
                    demo_lead = {
                        "id": "demo_001",
                        "name": "Demo Lead",
                        "phone": "+1234567890",
                        "email": "demo@example.com",
                        "company": "Demo Company"
                    }
                    lead_options["Demo Lead"] = demo_lead
                    
                    selected_display = st.radio(
                        "Select a lead:",
                        options=list(lead_options.keys()),
                        key="lead_selector"
                    )
                    
                    st.session_state.selected_lead = lead_options[selected_display]
                    st.write(f"**Selected:** {lead_options[selected_display]['name']}")
                    
                else:
                    # Fallback to demo lead
                    demo_lead = {
                        "id": "demo_001",
                        "name": "Demo Lead",
                        "phone": "+1234567890",
                        "email": "demo@example.com",
                        "company": "Demo Company"
                    }
                    st.write("**Using:** Demo Lead (no sheets leads found)")
                    st.session_state.selected_lead = demo_lead
            else:
                # No sheets configured, use demo
                demo_lead = {
                    "id": "demo_001",
                    "name": "Demo Lead",
                    "phone": "+1234567890",
                    "email": "demo@example.com",
                    "company": "Demo Company"
                }
                st.write("**Using:** Demo Lead (Sheets not configured)")
                st.session_state.selected_lead = demo_lead
        except Exception as e:
            st.warning(f"Could not load leads: {e}")
            demo_lead = {
                "id": "demo_001",
                "name": "Demo Lead",
                "phone": "+1234567890",
                "email": "demo@example.com",
                "company": "Demo Company"
            }
            st.write("**Using:** Demo Lead")
            st.session_state.selected_lead = demo_lead
        
        st.divider()
        
        # Voice settings
        st.header("Voice Settings")
        voice_options = ["nova", "shimmer", "alloy", "echo", "fable", "onyx"]
        selected_voice = st.selectbox(
            "Select Voice:",
            voice_options,
            index=0,
            key="voice_select"
        )
        
        st.divider()
        
        # Instructions
        st.markdown("""
        **How to use:**
        1. Click "Start Voice Call" to begin
        2. Click "🎤 Record Voice" to speak
        3. Your voice will be transcribed
        4. Agent will respond with voice
        5. Continue the conversation naturally
        
        **Features:**
        - 🎤 Voice input (STT)
        - 🔊 Voice output (TTS)
        - 🤖 AI-powered sales agent
        - 📅 Meeting scheduling
        """)
    
    # Main conversation area
    lead = st.session_state.selected_lead
    
    if lead is None:
        st.info("👈 Please configure a lead to start a voice call")
        return
    
    st.write(f"**Calling:** {lead['name']} ({lead['phone']})")
    
    # Start call button
    if st.session_state.session_id is None:
        if st.button("🎤 Start Voice Call", type="primary"):
            # Initialize conversation
            import time
            st.session_state.session_id = f"voice_{int(time.time())}"
            
            # Get initial greeting from agent
            try:
                # Use the regular trigger_call endpoint which will use the LangChain flow
                response = requests.post(
                    "http://localhost:8000/trigger_call",
                    json={"lead": lead}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.conversation_history = [{
                        "role": "agent",
                        "message": data['reply'],
                        "timestamp": "now"
                    }]
                    
                    # Speak the greeting
                    speak(data['reply'], voice=st.session_state.voice_select)
                    
                    st.rerun()
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Error starting call: {e}")
    else:
        # Display conversation history
        st.subheader("Conversation")
        
        for msg in st.session_state.conversation_history:
            if msg['role'] == 'agent':
                st.markdown(f"**🤖 Agent:** {msg['message']}")
            else:
                st.markdown(f"**👤 You:** {msg['message']}")
        
        # Check if conversation is done
        if st.session_state.conversation_done:
            st.success("✅ Call completed!")
            if st.button("Start New Voice Call"):
                st.session_state.session_id = None
                st.session_state.conversation_history = []
                st.session_state.conversation_done = False
                st.rerun()
        else:
            # Voice input section - CONTINUOUS MODE
            st.divider()
            st.subheader("🎤 Voice Call Mode")
            
            # Show current state for continuous mode
            if st.session_state.get('continuous_listening', False):
                # Don't show buttons while recording
                if not st.session_state.get('recording_vad', False):
                    st.info("🎤 Ready to listen. Click 'Speak Now' to start.")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if VAD_AVAILABLE:
                            if st.button("🎙️ Speak Now", type="primary"):
                                st.session_state.recording_vad = True
                                st.rerun()
                    
                    with col2:
                        if st.button("⏹️ End Call", type="secondary"):
                            st.session_state.continuous_listening = False
                            st.rerun()
            
            elif not st.session_state.get('continuous_listening', False) and VAD_AVAILABLE:
                if st.button("🎤 Start Continuous Call", type="primary"):
                    st.session_state.continuous_listening = True
                    st.session_state.ready_to_listen = True
                    st.rerun()
            
            # Audio clip recorder (backup option)
            if st.session_state.get('record_audio', False):
                st.info("🎤 Click the microphone icon below to record!")
                audio_data = st.audio_input("Record your response:", key="voice_recorder")
                
                if audio_data:
                    with st.spinner("🎤 Transcribing..."):
                        # Read bytes from UploadedFile
                        audio_bytes = audio_data.read()
                        
                        # Save to temp file
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                            temp_audio.write(audio_bytes)
                            temp_audio_path = temp_audio.name
                        
                        # Transcribe
                        transcript = transcribe_audio_with_whisper_api(temp_audio_path)
                        
                        # Clean up
                        if os.path.exists(temp_audio_path):
                            os.remove(temp_audio_path)
                        
                        if transcript:
                            st.success(f"🗣️ Transcribed: '{transcript}'")
                            st.session_state.user_input_fill = transcript
                            st.session_state.record_audio = False
                            st.rerun()
                        else:
                            st.error("Could not transcribe. Try again.")
            
            # VAD recording trigger - CONTINUOUS MODE (BLOCKING)
            if st.session_state.get('recording_vad', False):
                # Show listening indicator
                listen_placeholder = st.empty()
                listen_placeholder.info("🎤 Listening... Speak naturally (will auto-stop)")
                
                # Record (this blocks until speech ends)
                transcript = record_with_vad_continuous()
                
                # Clear listening indicator
                listen_placeholder.empty()
                st.session_state.recording_vad = False
                
                if transcript:
                    st.success(f"🗣️ Heard: '{transcript}'")
                    # Immediately process and send to agent
                    st.session_state.user_input_fill = transcript
                    # Keep continuous listening active for next turn
                    st.session_state.continuous_listening = True
                    st.rerun()
                else:
                    st.info("No speech detected. Try again!")
                    # Retry automatically in continuous mode
                    if st.session_state.get('continuous_listening', False):
                        st.session_state.recording_vad = True
                        st.rerun()
            
            # Check for auto-filled voice input and auto-continue
            if st.session_state.get('user_input_fill'):
                voice_input = st.session_state.user_input_fill
                st.session_state.user_input_fill = None
                st.session_state.voice_transcript = voice_input
                # Auto-continue listening after this
                st.session_state.continuous_listening = True
                st.rerun()
            
            # Process voice transcript
            if st.session_state.get('voice_transcript'):
                voice_input = st.session_state.voice_transcript
                st.session_state.voice_transcript = None
                
                # Send to agent
                with st.spinner("Agent is thinking..."):
                    try:
                        response = requests.post(
                            "http://localhost:8000/langchain/simulate",
                            json={
                                "session_id": st.session_state.session_id,
                                "lead": lead,
                                "user_input": voice_input  # Note: langchain endpoint uses "user_input" not "utterance"
                            }
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Add to history
                            st.session_state.conversation_history.append({
                                "role": "user",
                                "message": voice_input,
                                "timestamp": "now"
                            })
                            
                            st.session_state.conversation_history.append({
                                "role": "agent",
                                "message": data['reply'],
                                "timestamp": "now"
                            })
                            
                            # Speak agent response
                            speak(data['reply'], voice=st.session_state.voice_select)
                            
                            # Check if done
                            if data['final']:
                                st.session_state.conversation_done = True
                            
                            st.rerun()
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            # Text input fallback (for manual typing if needed)
            user_input = st.text_input(
                "Type response (optional):",
                key="manual_input"
            )
            
            if st.button("Send", key="send_text") and user_input:
                with st.spinner("Agent is thinking..."):
                    try:
                        response = requests.post(
                            "http://localhost:8000/langchain/simulate",
                            json={
                                "session_id": st.session_state.session_id,
                                "lead": lead,
                                "user_input": user_input  # Note: langchain endpoint uses "user_input" not "utterance"
                            }
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Add to history
                            st.session_state.conversation_history.append({
                                "role": "user",
                                "message": user_input,
                                "timestamp": "now"
                            })
                            
                            st.session_state.conversation_history.append({
                                "role": "agent",
                                "message": data['reply'],
                                "timestamp": "now"
                            })
                            
                            # Speak agent response
                            speak(data['reply'], voice=st.session_state.voice_select)
                            
                            # Check if done
                            if data['final']:
                                st.session_state.conversation_done = True
                            
                            st.rerun()
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")


if __name__ == "__main__":
    main()

