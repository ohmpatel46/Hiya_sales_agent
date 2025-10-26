"""
Voice-enabled sales call demo using OpenAI Whisper API and pyttsx3.

This demo integrates:
- OpenAI Whisper API for Speech-to-Text (online, requires API key)
- pyttsx3 for Text-to-Speech (local, offline)
- LangGraph conversation flow from demo.py

Usage:
    python -m agent.voice_demo
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent.state import Lead, ConversationState
from agent.graph import run_conversation_turn

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    print("[INFO] OpenAI client is available")
except ImportError:
    OPENAI_AVAILABLE = False
    print("[ERROR] OpenAI client not installed. Run: pip install openai")
    sys.exit(1)

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[WARNING] pygame not installed. Run: pip install pygame")
    print("[WARNING] Will use fallback TTS")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    print("[ERROR] speech_recognition not installed. Run: pip install SpeechRecognition")


# Import speech_recognition for the record function
if SR_AVAILABLE:
    sr = __import__("speech_recognition")


def speak_with_openai_tts(text: str, voice: str = "onyx", natural: bool = True) -> bool:
    """
    Speak text using OpenAI TTS API.
    
    Args:
        text: Text to speak
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        natural: Add natural pauses and phrasing
    
    Returns:
        True if successful, False otherwise
    """
    if not OPENAI_AVAILABLE:
        return False
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not set in .env file")
        return False
    
    # Prepare text for natural-sounding speech
    if natural:
        try:
            from agent.tts_helpers import prepare_text_for_speech
            text = prepare_text_for_speech(text, add_pauses=True)
        except ImportError:
            pass  # Fallback to original text
    
    if not PYGAME_AVAILABLE:
        print("[ERROR] pygame not available, cannot use OpenAI TTS")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Generate speech
        response = client.audio.speech.create(
            model="tts-1",  # Use tts-1 for speed, tts-1-hd for quality
            voice=voice,
            input=text
        )
        
        # Save to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            temp_audio.write(response.content)
            temp_audio_path = temp_audio.name
        
        # Play audio using pygame
        pygame.mixer.init()
        pygame.mixer.music.load(temp_audio_path)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Clean up before finishing
        pygame.mixer.music.stop()
        
        # Clean up
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        
        print(f"[Voice Demo] Spoke: '{text[:50]}...'")
        return True
        
    except Exception as e:
        print(f"[Voice Demo] TTS error: {e}")
        return False


def transcribe_audio_with_whisper_api(audio_file_path: str) -> str:
    """
    Transcribe audio using OpenAI Whisper API.
    
    Args:
        audio_file_path: Path to audio file (WAV, MP3, etc.)
    
    Returns:
        Transcribed text string
    """
    if not OPENAI_AVAILABLE:
        return ""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not set in .env file")
        return ""
    
    try:
        client = OpenAI(api_key=api_key)
        
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        return transcript.text.strip()
    except Exception as e:
        print(f"Whisper API error: {e}")
        return ""


def record_audio_with_speech_recognition() -> str:
    """
    Record audio from microphone using speech_recognition and save to file.
    Then transcribe with OpenAI Whisper API.
    
    Returns:
        Transcribed text or empty string
    """
    if not SR_AVAILABLE:
        return ""
    
    import tempfile
    import speech_recognition as sr_module
    recognizer = sr_module.Recognizer()
    
    try:
        with sr_module.Microphone() as source:
            print("[Voice Demo] Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            
            print("[Voice Demo] Listening... (speak now or press Enter to skip)")
            
            # Record audio
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
                temp_audio.write(audio.get_wav_data())
            
            print(f"[Voice Demo] Audio saved, transcribing with Whisper API...")
            
            # Transcribe with Whisper API
            transcript = transcribe_audio_with_whisper_api(temp_audio_path)
            
            # Clean up
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            
            if transcript:
                print(f"[Voice Demo] You said: '{transcript}'")
            
            return transcript
            
    except sr_module.WaitTimeoutError:
        print("[Voice Demo] No speech detected")
        return ""
    except Exception as e:
        print(f"[Voice Demo] Error: {e}")
        return ""


def run_voice_demo():
    """Run a voice-enabled sales call demo."""
    
    print("=" * 70)
    print("Autopitch AI - Voice-Enabled Sales Call Demo")
    print("Using: OpenAI Whisper (STT) + OpenAI TTS API")
    print("=" * 70)
    print("\nInstructions:")
    print("  • Speak your responses when prompted")
    print("  • Say 'exit' or 'quit' to end the conversation")
    print("  • The agent will speak back to you\n")
    
    # Initialize conversation
    lead = Lead(
        name="Demo Lead",
        phone="+1234567890",
        email="demo@example.com",
        company="Demo Company"
    )
    
    state = ConversationState(
        session_id="voice_demo_001",
        lead=lead,
        phase="intro"
    )
    
    # Initial greeting (hardcoded, not generated by LLM yet)
    initial_greeting = "Hi Demo Lead, this is your AI sales agent calling about Autopitch AI. Is now a good time to chat for a quick minute?"
    
    print(f"\nAgent: {initial_greeting}")
    speak_with_openai_tts(initial_greeting, voice="onyx")
    print()
    
    # Run conversation loop
    try:
        while True:
            # Get user input via voice
            print("\n[Listening... (speak now, or type to skip)]")
            user_input = input("You: ").strip()
            
            if not user_input:
                # Try voice input if not typed
                user_input = record_audio_with_speech_recognition()
                if not user_input:
                    continue
            
            # Check for exit
            if user_input.lower() in ['exit', 'quit', 'done', 'goodbye']:
                print("\n[Conversation ended]")
                speak_with_openai_tts("Thanks for your time. Have a great day!")
                break
            
            # Run turn
            state = run_conversation_turn(state, user_input)
            
            # Check if conversation ended
            if state.done:
                print("\n[Conversation ended]")
                print(f"[DEBUG] state.done = True, reason: {state.last_agent_reply}")
                
                # Speak the final message
                if state.last_agent_reply:
                    speak_with_openai_tts(state.last_agent_reply)
                
                break
            
            # Speak and print agent reply
            if state.last_agent_reply:
                print(f"\nAgent: {state.last_agent_reply}")
                speak_with_openai_tts(state.last_agent_reply)
                print()
    
    except KeyboardInterrupt:
        print("\n\n[Interrupted by user]")
        speak_with_openai_tts("Thanks for your time. Have a great day!")
    
    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    run_voice_demo()

