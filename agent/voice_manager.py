#!/usr/bin/env python3
"""
Voice Conversation Manager - Combines TTS and STT for voice conversations
"""
import time
from typing import Optional, Callable
from agent.tts import get_tts_service
from agent.stt import get_stt_service


class VoiceConversationManager:
    """Manages voice conversations with TTS and STT"""
    
    def __init__(self):
        self.tts = get_tts_service()
        self.stt = get_stt_service()
        self.is_listening = False
        self.conversation_active = False
    
    def start_conversation(self):
        """Start a voice conversation"""
        self.conversation_active = True
        print("Voice conversation started!")
    
    def end_conversation(self):
        """End the voice conversation"""
        self.conversation_active = False
        self.is_listening = False
        print("Voice conversation ended!")
    
    def speak_and_listen(self, text: str, timeout: int = 10, phrase_time_limit: int = 15) -> tuple[bool, str]:
        """
        Speak text and then listen for response
        
        Args:
            text: Text to speak
            timeout: Time to wait for speech to start
            phrase_time_limit: Maximum time to listen for a phrase
        
        Returns:
            Tuple of (success, transcribed_text)
        """
        if not self.conversation_active:
            return False, "Conversation not active"
        
        # Speak the text
        print(f"Speaking: {text[:50]}...")
        success = self.tts.speak(text)
        if not success:
            return False, "TTS failed"
        
        # Small pause after speaking
        time.sleep(0.5)
        
        # Listen for response
        print("Listening for response...")
        self.is_listening = True
        
        try:
            success, response = self.stt.listen_for_speech(timeout, phrase_time_limit)
            self.is_listening = False
            
            if success:
                print(f"User said: {response}")
                return True, response
            else:
                print(f"STT failed: {response}")
                return False, response
                
        except Exception as e:
            self.is_listening = False
            print(f"Voice conversation error: {e}")
            return False, str(e)
    
    def speak_only(self, text: str) -> bool:
        """Speak text without listening"""
        if not self.conversation_active:
            return False
        
        print(f"Speaking: {text[:50]}...")
        return self.tts.speak(text)
    
    def listen_only(self, timeout: int = 15, phrase_time_limit: int = 30) -> tuple[bool, str]:
        """Listen for speech without speaking"""
        if not self.conversation_active:
            return False, "Conversation not active"
        
        print("Listening...")
        self.is_listening = True
        
        try:
            success, response = self.stt.listen_for_speech(timeout, phrase_time_limit)
            self.is_listening = False
            
            if success:
                print(f"User said: {response}")
                return True, response
            else:
                print(f"STT failed: {response}")
                return False, response
                
        except Exception as e:
            self.is_listening = False
            print(f"Voice conversation error: {e}")
            return False, str(e)
    
    def run_voice_conversation(self, conversation_func: Callable[[str], str], initial_text: str):
        """
        Run a complete voice conversation
        
        Args:
            conversation_func: Function that takes user input and returns agent response
            initial_text: Initial text to speak
        """
        self.start_conversation()
        
        try:
            # Speak initial message
            current_text = initial_text
            
            while self.conversation_active:
                # Speak and listen
                success, user_input = self.speak_and_listen(current_text, timeout=10, phrase_time_limit=15)
                
                if not success:
                    print("Failed to get user input, ending conversation")
                    break
                
                # Get agent response
                try:
                    agent_response = conversation_func(user_input)
                    if not agent_response:
                        print("Agent returned empty response, ending conversation")
                        break
                    
                    current_text = agent_response
                    
                except Exception as e:
                    print(f"Error in conversation function: {e}")
                    current_text = "I apologize, but I'm having technical difficulties. Let me try to help you in a different way."
        
        finally:
            self.end_conversation()


# Global voice conversation manager
_voice_manager: Optional[VoiceConversationManager] = None


def get_voice_manager() -> VoiceConversationManager:
    """Get the global voice conversation manager"""
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceConversationManager()
    return _voice_manager


def speak_and_listen(text: str, timeout: int = 10, phrase_time_limit: int = 15) -> tuple[bool, str]:
    """Convenience function to speak and listen"""
    return get_voice_manager().speak_and_listen(text, timeout, phrase_time_limit)


def speak_only(text: str) -> bool:
    """Convenience function to speak only"""
    return get_voice_manager().speak_only(text)


def listen_only(timeout: int = 15, phrase_time_limit: int = 30) -> tuple[bool, str]:
    """Convenience function to listen only"""
    return get_voice_manager().listen_only(timeout, phrase_time_limit)


if __name__ == "__main__":
    # Test the voice conversation manager
    print("Testing Voice Conversation Manager")
    print("=" * 50)
    
    voice_manager = get_voice_manager()
    
    # Test speak only
    print("\n1. Testing speak only...")
    voice_manager.start_conversation()
    success = voice_manager.speak_only("Hello! This is a test of the voice conversation manager.")
    print(f"Speak only result: {success}")
    
    # Test listen only
    print("\n2. Testing listen only...")
    print("Say something!")
    success, text = voice_manager.listen_only(timeout=5, phrase_time_limit=10)
    print(f"Listen only result: {success}, text: '{text}'")
    
    # Test speak and listen
    print("\n3. Testing speak and listen...")
    print("I'll ask you a question, please respond!")
    success, response = voice_manager.speak_and_listen(
        "What is your name?", 
        timeout=5, 
        phrase_time_limit=10
    )
    print(f"Speak and listen result: {success}, response: '{response}'")
    
    voice_manager.end_conversation()
    print("\nVoice conversation test completed!")
