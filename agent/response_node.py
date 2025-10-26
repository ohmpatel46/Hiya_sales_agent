"""
Response node - the main node that "talks like an SDR"

This node:
1. Classifies intent from user_utterance and saves to state.intent
2. Detects tone from user_utterance and saves to state.tone
3. Extracts any scheduling info ("tomorrow at 2pm") into state.slots
4. Decides next_action via decide_next_action(state)
5. Uses LangChain generate_reply_chain(...) to craft ONE human-sounding agent reply:
   - acknowledges what they said
   - matches tone (friendly/rushed/skeptical/etc)
   - ends with a CTA appropriate to next_action
6. Saves that reply into state.last_agent_reply for the simulator to speak/print
7. Sets state.phase = next_action so downstream nodes can branch on it
8. Returns the mutated state

IMPORTANT: This node does not actually finalize scheduling or mark done.
It just nudges them toward the next step verbally, in a natural SDR-like way.
"""

from agent.state import ConversationState
from agent.llm_tools import classify_intent_chain, detect_tone_chain, generate_reply_chain
from agent.planner import extract_datetime, decide_next_action


def bridge_and_nudge_node(state: ConversationState, user_utterance: str) -> ConversationState:
    """
    The main conversational node that generates agent replies.
    
    This is where LangChain is used to generate human-sounding responses.
    The node:
    - Uses classify_intent_chain() to understand what the lead wants
    - Uses detect_tone_chain() to match their energy level
    - Uses extract_datetime() to pull out scheduling info
    - Uses decide_next_action() for deterministic business strategy
    - Uses generate_reply_chain() to craft the reply with LangChain
    
    Args:
        state: Current conversation state
        user_utterance: What the lead just said
    
    Returns:
        Updated conversation state with last_agent_reply and phase set
    """
    
    # 1. Classify intent (using LangChain if needed)
    intent_result = classify_intent_chain(user_utterance)
    state.intent = intent_result["intent"]
    
    # 2. Detect tone with confidence score (heuristic + optional LLM)
    tone_result = detect_tone_chain(user_utterance)
    state.tone = tone_result[0]
    state.tone_confidence = tone_result[1]
    print(f"[DEBUG] Tone detected: {state.tone} (confidence: {state.tone_confidence:.2f})")
    
    # 3. Extract datetime if present
    extract_datetime(user_utterance, state)
    
    # 4. Decide next action (deterministic Python logic)
    next_action = decide_next_action(state)
    print(f"[DEBUG] Next action decided: {next_action}")
    state.phase = next_action  # Set phase for downstream routing
    
    # 5. Generate reply using LangChain (this is where LLM is used)
    # The LLM only phrases the response - it doesn't choose strategy
    agent_reply = generate_reply_chain(state, user_utterance, next_action)
    print(f"[DEBUG] Generated agent reply: {agent_reply[:100]}...")
    
    # 6. Save the reply
    state.last_agent_reply = agent_reply
    
    # 7. Track conversation history for context
    turn_number = len(state.conversation_history) + 1
    state.conversation_history.append({
        "user": user_utterance,
        "agent": agent_reply,
        "intent": state.intent,
        "tone": state.tone,
        "tone_confidence": state.tone_confidence,
        "turn": turn_number,
        "phase": state.phase
    })
    print(f"[DEBUG] Conversation history: {len(state.conversation_history)} turns")
    
    # 8. Return updated state
    return state

