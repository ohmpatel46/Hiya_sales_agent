#!/usr/bin/env python3
"""
Speech-to-Text (STT) service for the sales agent
"""
import speech_recognition as sr
import time
from typing import Optional, Tuple


class STTService:
    """Speech-to-Text service using Google Speech Recognition"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self._initialize_microphone()
    
    def _initialize_microphone(self):
        """Initialize the microphone"""
        try:
            self.microphone = sr.Microphone()
            print("Microphone initialized successfully")
        except Exception as e:
            print(f"Failed to initialize microphone: {e}")
            self.microphone = None
    
    def listen_for_speech(self, timeout: int = 5, phrase_time_limit: int = 10) -> Tuple[bool, str]:
        """
        Listen for speech input
        
        Args:
            timeout: Maximum time to wait for speech to start
            phrase_time_limit: Maximum time to listen for a phrase
        
        Returns:
            Tuple of (success, transcribed_text)
        """
        if not self.microphone:
            return False, "Microphone not available"
        
        try:
            print("Listening for speech...")
            
            # Adjust for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Listen for audio
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
            
            print("Processing speech...")
            
            # Recognize speech using Google Speech Recognition
            text = self.recognizer.recognize_google(audio)
            
            print(f"STT Heard: {text}")
            return True, text
            
        except sr.WaitTimeoutError:
            print("STT Timeout: No speech detected")
            return False, "No speech detected"
        except sr.UnknownValueError:
            print("STT Error: Could not understand speech")
            return False, "Could not understand speech"
        except sr.RequestError as e:
            print(f"STT Error: {e}")
            return False, f"Speech recognition error: {e}"
        except Exception as e:
            print(f"STT Unexpected error: {e}")
            return False, f"Unexpected error: {e}"
    
    def listen_with_callback(self, callback_func, timeout: int = 5, phrase_time_limit: int = 10):
        """
        Listen for speech and call a callback function with the result
        
        Args:
            callback_func: Function to call with (success, text) tuple
            timeout: Maximum time to wait for speech to start
            phrase_time_limit: Maximum time to listen for a phrase
        """
        success, text = self.listen_for_speech(timeout, phrase_time_limit)
        callback_func(success, text)
    
    def get_microphone_list(self) -> list:
        """Get list of available microphones"""
        try:
            return sr.Microphone.list_microphone_names()
        except Exception as e:
            print(f"Error getting microphone list: {e}")
            return []
    
    def set_microphone(self, device_index: int) -> bool:
        """Set microphone by device index"""
        try:
            self.microphone = sr.Microphone(device_index=device_index)
            return True
        except Exception as e:
            print(f"Error setting microphone: {e}")
            return False


# Global STT service instance
_stt_service: Optional[STTService] = None


def get_stt_service() -> STTService:
    """Get the global STT service instance"""
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService()
    return _stt_service


def listen_for_speech(timeout: int = 5, phrase_time_limit: int = 10) -> Tuple[bool, str]:
    """Convenience function to listen for speech"""
    return get_stt_service().listen_for_speech(timeout, phrase_time_limit)


if __name__ == "__main__":
    # Test the STT service
    print("Testing STT Service")
    print("=" * 40)
    
    stt = get_stt_service()
    
    # Show available microphones
    mics = stt.get_microphone_list()
    print(f"Available microphones: {len(mics)}")
    for i, mic in enumerate(mics):
        print(f"  {i}: {mic}")
    
    # Test listening
    print("\nListening for speech (5 second timeout)...")
    print("Say something!")
    
    success, text = stt.listen_for_speech(timeout=5, phrase_time_limit=10)
    
    if success:
        print(f"OK STT successful: '{text}'")
    else:
        print(f"ERROR STT failed: {text}")
