from typing import Dict, Any, Optional
from agent.schemas import SessionState, Lead, TraceTurn, ToolCall
from agent.flows.sales import next_agent_reply
from agent.tools import calendar, crm_stub
from agent.tts import speak_text
from agent.evaluation import evaluate_conversation


# In-memory session storage (for MVP)
sessions: Dict[str, SessionState] = {}


def handle_turn(session_id: str, lead: Lead, user_text: str) -> Dict[str, Any]:
    """
    Handle a conversation turn
    
    Args:
        session_id: Unique session identifier
        lead: Lead information
        user_text: User's utterance
    
    Returns:
        Dict with reply, state, and tool results
    """
    # Ensure session exists
    if session_id not in sessions:
        sessions[session_id] = SessionState(
            session_id=session_id,
            lead=lead,
            slots={},
            history=[],
            done=False
        )
    
    session = sessions[session_id]
    
    # Update lead if provided
    if lead:
        session.lead = lead
    
    try:
        # Get agent response from sales flow
        response = next_agent_reply(session, user_text)
        
        # Execute tool calls
        tool_results = []
        for tool_call in response.get("tool_calls", []):
            result = _execute_tool_call(tool_call)
            tool_results.append(result)
        
        # Create trace turn
        trace_turn = TraceTurn(
            user=user_text,
            agent=response["reply"],
            tool_calls=response.get("tool_calls", []),
            tool_results=tool_results,
            state=session.dict()
        )
        
        # Add to history
        session.history.append(trace_turn)
        
        # Mark as done if final
        if response.get("final", False):
            session.done = True
            # Evaluate the conversation
            try:
                outcome = "interested" if any("calendar.create_event" in str(tc.name) for tc in response.get("tool_calls", [])) else "not_interested"
                evaluate_conversation(session, outcome)
            except Exception as e:
                print(f"Evaluation error: {e}")
        
        # TTS is handled by the voice sales agent, not here
        # try:
        #     speak_text(response["reply"])
        # except Exception as e:
        #     print(f"TTS error: {e}")
        
        return {
            "reply": response["reply"],
            "state": session.dict(),
            "tool_results": tool_results,
            "final": response.get("final", False)
        }
        
    except Exception as e:
        # Handle errors gracefully
        error_reply = "I apologize, but I'm having some technical difficulties. Let me try to help you in a different way. What would you like to know about our AI sales agent?"
        
        trace_turn = TraceTurn(
            user=user_text,
            agent=error_reply,
            tool_calls=[],
            tool_results=[{"error": str(e)}],
            state=session.dict()
        )
        
        session.history.append(trace_turn)
        
        return {
            "reply": error_reply,
            "state": session.dict(),
            "tool_results": [{"error": str(e)}],
            "final": False
        }


def _execute_tool_call(tool_call: ToolCall) -> Dict[str, Any]:
    """Execute a tool call and return results"""
    try:
        if tool_call.name == "calendar.create_event":
            return calendar.create_event(**tool_call.args)
        elif tool_call.name == "crm_stub.log_outcome":
            return crm_stub.log_outcome(**tool_call.args)
        elif tool_call.name == "crm_stub.log_followup":
            return crm_stub.log_followup(**tool_call.args)
        else:
            return {
                "error": f"Unknown tool: {tool_call.name}",
                "tool_call": tool_call.dict()
            }
    except Exception as e:
        return {
            "error": str(e),
            "tool_call": tool_call.dict()
        }


def get_session(session_id: str) -> Optional[SessionState]:
    """Get session state by ID"""
    return sessions.get(session_id)


def create_session(session_id: str, lead: Lead) -> SessionState:
    """Create a new session"""
    session = SessionState(
        session_id=session_id,
        lead=lead,
        slots={},
        history=[],
        done=False
    )
    sessions[session_id] = session
    return session


def clear_session(session_id: str) -> bool:
    """Clear a session (for testing)"""
    if session_id in sessions:
        del sessions[session_id]
        return True
    return False
