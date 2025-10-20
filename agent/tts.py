#!/usr/bin/env python3
"""
Text-to-Speech (TTS) service for the sales agent
"""
import pyttsx3
import tempfile
import os
from typing import Optional
from pathlib import Path


class TTSService:
    """Text-to-Speech service using pyttsx3"""
    
    def __init__(self):
        self.engine = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the TTS engine"""
        try:
            self.engine = pyttsx3.init()
            
            # Configure voice settings
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to find a female voice (more natural for sales calls)
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
                else:
                    # Fallback to first available voice
                    self.engine.setProperty('voice', voices[0].id)
            
            # Set speech rate (words per minute)
            self.engine.setProperty('rate', 180)  # Slightly slower for clarity
            
            # Set volume (0.0 to 1.0)
            self.engine.setProperty('volume', 0.9)
            
        except Exception as e:
            print(f"Failed to initialize TTS engine: {e}")
            self.engine = None
    
    def speak(self, text: str) -> bool:
        """Speak the given text"""
        if not self.engine:
            print("TTS engine not initialized")
            return False
        
        try:
            print(f"TTS Speaking: {text[:50]}...")
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"TTS error: {e}")
            return False
    
    def save_to_file(self, text: str, filename: Optional[str] = None) -> Optional[str]:
        """Save speech to audio file"""
        if not self.engine:
            print("TTS engine not initialized")
            return None
        
        try:
            if not filename:
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                filename = temp_file.name
                temp_file.close()
            
            print(f"TTS Saving to file: {filename}")
            self.engine.save_to_file(text, filename)
            self.engine.runAndWait()
            
            # Check if file was created
            if os.path.exists(filename):
                return filename
            else:
                print("Failed to create audio file")
                return None
                
        except Exception as e:
            print(f"TTS file save error: {e}")
            return None
    
    def get_available_voices(self) -> list:
        """Get list of available voices"""
        if not self.engine:
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            return [{'id': voice.id, 'name': voice.name} for voice in voices]
        except Exception as e:
            print(f"Error getting voices: {e}")
            return []
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the voice by ID"""
        if not self.engine:
            return False
        
        try:
            self.engine.setProperty('voice', voice_id)
            return True
        except Exception as e:
            print(f"Error setting voice: {e}")
            return False
    
    def set_rate(self, rate: int) -> bool:
        """Set speech rate (words per minute)"""
        if not self.engine:
            return False
        
        try:
            self.engine.setProperty('rate', rate)
            return True
        except Exception as e:
            print(f"Error setting rate: {e}")
            return False
    
    def set_volume(self, volume: float) -> bool:
        """Set volume (0.0 to 1.0)"""
        if not self.engine:
            return False
        
        try:
            self.engine.setProperty('volume', max(0.0, min(1.0, volume)))
            return True
        except Exception as e:
            print(f"Error setting volume: {e}")
            return False


# Global TTS service instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get the global TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


def speak_text(text: str) -> bool:
    """Convenience function to speak text"""
    return get_tts_service().speak(text)


def save_speech_to_file(text: str, filename: Optional[str] = None) -> Optional[str]:
    """Convenience function to save speech to file"""
    return get_tts_service().save_to_file(text, filename)


if __name__ == "__main__":
    # Test the TTS service
    print("Testing TTS Service")
    print("=" * 40)
    
    tts = get_tts_service()
    
    # Show available voices
    voices = tts.get_available_voices()
    print(f"Available voices: {len(voices)}")
    for voice in voices:
        print(f"  - {voice['name']} ({voice['id']})")
    
    # Test speaking
    test_text = "Hello! This is your AI sales agent calling about our AI call agent service."
    print(f"\nSpeaking: {test_text}")
    
    success = tts.speak(test_text)
    if success:
        print("OK TTS test successful!")
    else:
        print("ERROR TTS test failed!")
    
    # Test saving to file
    print("\nTesting file save...")
    audio_file = tts.save_to_file("This is a test of saving speech to a file.")
    if audio_file:
        print(f"OK Audio saved to: {audio_file}")
        print(f"File size: {os.path.getsize(audio_file)} bytes")
    else:
        print("ERROR Failed to save audio file")
