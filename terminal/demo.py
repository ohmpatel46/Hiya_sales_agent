"""
Simulated call loop for testing the LangGraph sales agent.

This allows you to test the conversation flow by playing the role of the lead.
The agent responds using LangChain for phrasing and LangGraph for orchestration.

Example interaction:
    Lead: yeah this sounds interesting but I'm in a meeting
    Agent: Totally get that. I can keep it quick — should I call you later today or is tomorrow morning better?
    
    Lead: tomorrow morning works
    Agent: Perfect. I'll lock a quick slot for tomorrow morning and send over a short summary. Talk soon.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent.state import Lead, ConversationState
from agent.graph import run_conversation_turn


def run_demo():
    """Run a simulated sales call in the terminal."""
    
    print("=" * 70)
    print("Autopitch AI - Sales Agent Demo (LangGraph + LangChain)")
    print("=" * 70)
    print("\nWelcome! You're the lead. Type your responses to interact with the agent.")
    print("Type 'exit' or 'quit' to end the conversation.\n")
    
    # Initialize conversation
    lead = Lead(
        name="Demo Lead",
        phone="+1234567890",
        email="demo@example.com",
        company="Demo Company"
    )
    
    state = ConversationState(
        session_id="demo_session",
        phase="intro",
        lead=lead,
        slots={},
        done=False
    )
    
    # Send initial greeting - ask if it's a good time first
    print("Agent: Hi Demo Lead, this is your AI sales agent calling about Autopitch AI. Is now a good time to chat for a quick minute?\n")
    
    # Update phase to intro for first turn  
    state.phase = "intro"
    # Store the initial greeting in state so it doesn't get regenerated
    state.last_agent_reply = None
    
    # Get first response to see if they're busy
    try:
        user_input = input("Lead: ").strip()
        if not user_input or user_input.lower() in ["exit", "quit"]:
            print("\nExiting conversation.")
            return
        
        # Run first turn through LangGraph
        state = run_conversation_turn(state, user_input)
        
        # Check if they immediately said they're busy
        user_lower = user_input.lower()
        is_busy_response = any(word in user_lower for word in ["busy", "not a good time", "meeting", "in a meeting", "can't talk"])
        
        if is_busy_response and "intro" in state.phase:
            # They're busy, handle gracefully
            state = run_conversation_turn(state, user_input)
        
        # Print agent response
        if state.last_agent_reply:
            print(f"\nAgent: {state.last_agent_reply}\n")
        else:
            # Provide default summary if no reply generated
            print("\nAgent: No worries at all! I'll keep this super quick — we help sales teams automate lead qualification and demo booking with AI. Should I call you back later today or tomorrow morning?\n")
    except Exception as e:
        print(f"\n[DEBUG] Error in first turn: {e}")
        print("\nAgent: No worries at all! I'll keep this super quick — we help sales teams automate lead qualification and demo booking with AI. Should I call you back later today or tomorrow morning?\n")
        state.phase = "reschedule"
    
    # Conversation loop
    while not state.done:
        try:
            # Get user input
            user_input = input("Lead: ").strip()
            
            if not user_input or user_input.lower() in ["exit", "quit"]:
                print("\nExiting conversation.")
                break
            
            # Run turn through LangGraph
            state = run_conversation_turn(state, user_input)
            
            # Print agent response
            if state.last_agent_reply:
                print(f"\nAgent: {state.last_agent_reply}\n")
            
            # Check if done
            if state.done:
                print("\n[Conversation ended]")
                print(f"[DEBUG] state.done = {state.done}, reason: check conversation state")
                break
            
        except KeyboardInterrupt:
            print("\n\nExiting conversation.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()

