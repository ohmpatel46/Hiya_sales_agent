#!/usr/bin/env python3
"""
Voice Sales Agent - Complete voice-enabled sales conversation
"""
from agent.schemas import Lead
from agent.orchestrator import handle_turn, clear_session
from agent.voice_manager import get_voice_manager


class VoiceSalesAgent:
    """Voice-enabled sales agent"""
    
    def __init__(self):
        self.voice_manager = get_voice_manager()
        self.current_session_id = None
        self.current_lead = None
    
    def start_voice_call(self, lead: Lead) -> bool:
        """Start a voice sales call with a lead"""
        try:
            # Clear any existing session
            if self.current_session_id:
                clear_session(self.current_session_id)
            
            # Start new session
            self.current_session_id = f"voice_call_{lead.id}"
            self.current_lead = lead
            
            # Start voice conversation
            self.voice_manager.start_conversation()
            
            # Get initial agent response
            response = handle_turn(self.current_session_id, lead, "")
            
            if response and response.get("reply"):
                # Speak the initial greeting
                success = self.voice_manager.speak_only(response["reply"])
                if success:
                    print(f"Started voice call with {lead.name}")
                    return True
                else:
                    print("Failed to speak initial greeting")
                    return False
            else:
                print("Failed to get initial response")
                return False
                
        except Exception as e:
            print(f"Error starting voice call: {e}")
            return False
    
    def continue_voice_conversation(self) -> bool:
        """Continue the voice conversation"""
        if not self.current_session_id or not self.current_lead:
            print("No active voice call")
            return False
        
        try:
            # Listen for user response
            success, user_input = self.voice_manager.listen_only(timeout=15, phrase_time_limit=30)
            
            if not success:
                print(f"Failed to get user input: {user_input}")
                return False
            
            # Process user input through sales flow
            response = handle_turn(self.current_session_id, self.current_lead, user_input)
            
            if response and response.get("reply"):
                # Speak the agent response
                success = self.voice_manager.speak_only(response["reply"])
                if success:
                    # Check if conversation is done
                    if response.get("final", False):
                        print("Voice call completed!")
                        self.end_voice_call()
                        return False  # Conversation ended
                    return True
                else:
                    print("Failed to speak agent response")
                    return False
            else:
                print("Failed to get agent response")
                return False
                
        except Exception as e:
            print(f"Error in voice conversation: {e}")
            return False
    
    def run_complete_voice_call(self, lead: Lead):
        """Run a complete voice sales call"""
        if not self.start_voice_call(lead):
            return
        
        try:
            # Continue conversation until done
            while True:
                if not self.continue_voice_conversation():
                    break
        except KeyboardInterrupt:
            print("\nVoice call interrupted by user")
        except Exception as e:
            print(f"Error in voice call: {e}")
        finally:
            self.end_voice_call()
    
    def end_voice_call(self):
        """End the current voice call"""
        if self.voice_manager:
            self.voice_manager.end_conversation()
        
        self.current_session_id = None
        self.current_lead = None
        print("Voice call ended")
    
    def get_call_status(self) -> dict:
        """Get current call status"""
        return {
            "active": self.current_session_id is not None,
            "session_id": self.current_session_id,
            "lead": self.current_lead.dict() if self.current_lead else None,
            "listening": self.voice_manager.is_listening if self.voice_manager else False
        }


# Global voice sales agent
_voice_sales_agent: VoiceSalesAgent = None


def get_voice_sales_agent() -> VoiceSalesAgent:
    """Get the global voice sales agent"""
    global _voice_sales_agent
    if _voice_sales_agent is None:
        _voice_sales_agent = VoiceSalesAgent()
    return _voice_sales_agent


def start_voice_call(lead: Lead) -> bool:
    """Convenience function to start a voice call"""
    return get_voice_sales_agent().start_voice_call(lead)


def continue_voice_conversation() -> bool:
    """Convenience function to continue voice conversation"""
    return get_voice_sales_agent().continue_voice_conversation()


def run_complete_voice_call(lead: Lead):
    """Convenience function to run complete voice call"""
    return get_voice_sales_agent().run_complete_voice_call(lead)


def end_voice_call():
    """Convenience function to end voice call"""
    return get_voice_sales_agent().end_voice_call()


if __name__ == "__main__":
    # Test the voice sales agent
    print("Testing Voice Sales Agent")
    print("=" * 50)
    
    # Create a test lead
    test_lead = Lead(
        id="voice_test",
        name="Test User",
        phone="+1-555-123-4567",
        email="test@example.com",
        company="Test Corp"
    )
    
    print(f"Starting voice call with {test_lead.name}...")
    print("The agent will speak the greeting, then listen for your response.")
    print("Press Ctrl+C to end the call early.")
    
    # Run the complete voice call
    run_complete_voice_call(test_lead)
    
    print("Voice sales agent test completed!")
