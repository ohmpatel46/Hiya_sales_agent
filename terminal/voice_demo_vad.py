"""
Voice-enabled sales call demo with Voice Activity Detection (VAD).

Uses webrtcvad for automatic end-of-silence detection - much more natural!
"""

import os
import sys
from dotenv import load_dotenv

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

try:
    import pyaudio
    import webrtcvad
    VAD_AVAILABLE = True
    print("[INFO] VAD is available")
except ImportError:
    VAD_AVAILABLE = False
    print("[ERROR] webrtcvad not installed. Run: pip install webrtcvad pyaudio")


def speak_with_openai_tts(text: str, voice: str = "onyx", natural: bool = True) -> bool:
    """
    Speak text using OpenAI TTS API.
    
    Args:
        text: Text to speak
        voice: Voice to use (nova, shimmer, alloy, echo, fable, onyx)
        natural: Add natural pauses and phrasing
    """
    if not OPENAI_AVAILABLE:
        return False
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False
    
    # Prepare text for natural-sounding speech
    if natural:
        try:
            from agent.tts_helpers import prepare_text_for_speech
            text = prepare_text_for_speech(text, add_pauses=True)
        except ImportError:
            pass  # Fallback to original text
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Generate speech
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Save to temp file
        import tempfile
        temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_audio.write(response.content)
        temp_audio_path = temp_audio.name
        temp_audio.close()
        
        # Play audio
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(temp_audio_path)
        pygame.mixer.music.play()
        
        # Wait for playback to complete
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Stop and unload before deleting
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        
        # Now safe to delete
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass  # File might be locked, that's okay
        
        return True
    except Exception as e:
        print(f"TTS error: {e}")
        return False


def transcribe_audio_with_whisper_api(audio_file_path: str) -> str:
    """Transcribe audio using OpenAI Whisper API."""
    if not OPENAI_AVAILABLE:
        return ""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
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


def record_with_vad() -> str:
    """
    Record audio with Voice Activity Detection - automatically stops when silence is detected.
    Much more natural than fixed timeouts!
    """
    if not VAD_AVAILABLE:
        print("[ERROR] VAD not available. Install: pip install webrtcvad")
        return ""
    
    p = pyaudio.PyAudio()
    
    # Audio format - VAD requires specific settings
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000  # 16kHz is good balance for VAD
    
    # VAD requires frame size for 10ms, 20ms, or 30ms
    # For 16kHz: 10ms = 160 samples, 20ms = 320 samples, 30ms = 480 samples
    FRAME_DURATION_MS = 30  # Use 30ms frames
    CHUNK = int(RATE * FRAME_DURATION_MS / 1000)  # 480 samples for 30ms at 16kHz
    
    # VAD settings
    vad = webrtcvad.Vad(2)  # 0=quality mode, 3=aggressive mode, 2=balanced
    
    # Parameters for end-of-speech detection
    SILENCE_DURATION = 2  # Seconds of silence to stop
    
    silence_frames = 0
    frames = []
    
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print("[Voice] Listening... (speak now)")
        
        # Record until silence detected
        recording = True
        speech_detected = False
        
        while recording:
            chunk = stream.read(CHUNK, exception_on_overflow=False)
            
            # VAD requires exactly the right chunk size (30ms at 16kHz = 480 bytes for paInt16)
            expected_bytes = CHUNK * 2  # paInt16 = 2 bytes per sample
            
            try:
                # Check if speech detected
                is_speech = vad.is_speech(chunk, RATE)
                
                if is_speech:
                    silence_frames = 0
                    speech_detected = True
                else:
                    if speech_detected:  # Only count silence after speech has been detected
                        silence_frames += 1
                        
                        # Stop if silence threshold reached
                        silence_duration = (silence_frames * FRAME_DURATION_MS) / 1000.0
                        if silence_duration >= SILENCE_DURATION:
                            print(f"[Voice] End of speech detected ({len(frames)} frames)")
                            recording = False
                            break
                
                frames.append(chunk)
            except webrtcvad.Error as e:
                # VAD frame size error - this shouldn't happen but skip if it does
                continue
            except Exception as e:
                # Other error, continue recording without VAD
                print(f"[Voice] VAD warning: {e}")
                frames.append(chunk)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
    except Exception as e:
        print(f"[Voice] Recording error: {e}")
        p.terminate()
    
    if not frames:
        return ""
    
    # Save to temp file
    import tempfile
    import wave
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio_path = temp_audio.name
        
        # Write WAV file
        wf = wave.open(temp_audio_path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
    
    # Transcribe
    print("[Voice] Transcribing...")
    transcript = transcribe_audio_with_whisper_api(temp_audio_path)
    
    # Clean up
    if os.path.exists(temp_audio_path):
        os.remove(temp_audio_path)
    
    if transcript:
        print(f"[Voice] You said: '{transcript}'")
    
    return transcript


def run_voice_demo():
    """Run a voice-enabled sales call demo with VAD."""
    
    print("=" * 70)
    print("Autopitch AI - Voice-Enabled Sales Call Demo")
    print("Using: OpenAI Whisper API + OpenAI TTS API + VAD")
    print("=" * 70)
    print("\nInstructions:")
    print("  • Speak your responses - it will auto-detect when you stop")
    print("  • Say 'exit' or 'quit' to end the conversation")
    print("  • The agent will speak back to you\n")
    
    if not VAD_AVAILABLE:
        print("[ERROR] VAD not available. Falling back to basic recording.")
        print("Install: pip install webrtcvad pyaudio")
    
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
    
    # Initial greeting
    initial_greeting = "Hi Demo Lead, this is your AI sales agent calling about Autopitch AI. Is now a good time to chat for a quick minute?"
    
    print(f"\nAgent: {initial_greeting}")
    speak_with_openai_tts(initial_greeting, voice="onyx")
    print()
    
    # Run conversation loop
    try:
        while True:
            # Get user input via voice
            print("\n[Listening... (press 't' to type, or speak to record)]")
            
            # Always try VAD first
            if VAD_AVAILABLE:
                user_input = record_with_vad()
                if not user_input:
                    # Allow typing fallback
                    print("\n[No speech detected or VAD interrupted. Type your response:]")
                    user_input = input("You: ").strip()
            else:
                # Fallback to typing
                user_input = input("You (VAD unavailable, type response): ").strip()
            
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

