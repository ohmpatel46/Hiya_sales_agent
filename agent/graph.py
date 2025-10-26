"""
LangGraph orchestration for the sales conversation flow.

This file defines the actual LangGraph graph that orchestrates the conversation.
The graph uses LangGraph.StateGraph to create a state machine.

Key nodes:
- bridge_and_nudge: Produces the next spoken line, sets phase=next_action
- route_next_action: Branches to appropriate path
- schedule_path: Handles meeting scheduling
- send_info_path: Handles sending information
- not_interested_path: Handles polite exits
- close_out: Final cleanup

The graph is deterministic and auditable. The agent can only go down
approved paths toward allowed exits. This keeps us in control of
business logic while letting the LLM handle phrasing.
"""

from langgraph.graph import StateGraph, END
from agent.state import ConversationState
from agent.response_node import bridge_and_nudge_node
from agent.path_nodes import (
    schedule_path_node, send_info_path_node, not_interested_node, 
    provide_info_node, provide_more_info_node, answer_question_node, close_out_node
)
from typing import Dict, Any, Optional

# Global sessions storage for API endpoints
sessions: Dict[str, ConversationState] = {}


def bridge_adapter(state: ConversationState) -> ConversationState:
    """
    Adapter for bridge_and_nudge_node.
    
    Retrieves user_utterance from state and passes it to the node.
    """
    user_utterance = state.current_user_utterance or ""
    return bridge_and_nudge_node(state, user_utterance)


def route_next_action(state: ConversationState) -> ConversationState:
    """
    Routing node - just passes through the state.
    
    No mutation needed here. state.phase already holds next_action
    like "propose_meeting", "ask_channel_pref", etc. from the previous node.
    
    The conditional edges will use state.phase to route to the right path.
    """
    return state


def schedule_adapter(state: ConversationState) -> ConversationState:
    """Adapter for schedule_path_node."""
    user_utterance = state.current_user_utterance or ""
    return schedule_path_node(state, user_utterance)


def send_info_adapter(state: ConversationState) -> ConversationState:
    """Adapter for send_info_path_node."""
    user_utterance = state.current_user_utterance or ""
    return send_info_path_node(state, user_utterance)


def not_interested_adapter(state: ConversationState) -> ConversationState:
    """Adapter for not_interested_node."""
    user_utterance = state.current_user_utterance or ""
    return not_interested_node(state, user_utterance)


def create_sales_agent_graph():
    """
    Create and compile the LangGraph sales agent.
    
    Returns:
        Compiled StateGraph ready to run
    """
    
    # Create the graph
    graph = StateGraph(ConversationState)
    
    # Add nodes
    graph.add_node("bridge_and_nudge", bridge_adapter)
    graph.add_node("route_next_action", route_next_action)
    graph.add_node("schedule_path", schedule_adapter)
    graph.add_node("send_info_path", send_info_adapter)
    graph.add_node("not_interested_path", not_interested_adapter)
    graph.add_node("provide_info_path", lambda state: provide_info_node(state, state.current_user_utterance or ""))
    graph.add_node("provide_more_info_path", lambda state: provide_more_info_node(state, state.current_user_utterance or ""))
    graph.add_node("answer_question_path", lambda state: answer_question_node(state, state.current_user_utterance or ""))
    graph.add_node("close_out", lambda state: close_out_node(state))
    
    # Define the flow
    # Start with bridge_and_nudge
    graph.set_entry_point("bridge_and_nudge")
    
    # bridge_and_nudge always goes to route_next_action
    graph.add_edge("bridge_and_nudge", "route_next_action")
    
    # route_next_action branches based on state.phase
    graph.add_conditional_edges(
        "route_next_action",
        lambda state: state.phase,  # Branch on the phase/next_action
        {
            # Map planner outputs to path nodes
            "confirm_meeting": "schedule_path",  # Confirm extracted datetime
            "propose_meeting": "schedule_path",
            "reschedule": "schedule_path",
            "clarify_time": "schedule_path",
            "propose_specific_time": "schedule_path",  # Propose specific time (e.g., "tomorrow at 2pm?")
            
            "provide_info": "provide_info_path",  # Provide company info to interested leads
            "provide_more_info": "provide_more_info_path",  # Provide additional detailed info
            "answer_question": "answer_question_path",  # Answer questions using company info
            
            "ask_channel_pref": "send_info_path",
            
            "graceful_exit": "not_interested_path",
            
            "ask_for_clarification": "schedule_path"
        }
    )
    
    # All paths converge on close_out
    graph.add_edge("schedule_path", "close_out")
    graph.add_edge("send_info_path", "close_out")
    graph.add_edge("not_interested_path", "close_out")
    graph.add_edge("provide_info_path", "close_out")
    graph.add_edge("provide_more_info_path", "close_out")
    graph.add_edge("answer_question_path", "close_out")
    
    # close_out ends the graph
    graph.add_edge("close_out", END)
    
    # Compile the graph
    sales_agent_graph = graph.compile()
    
    return sales_agent_graph


# Module-level instance
_sales_agent_graph: Optional[Any] = None


def get_sales_agent_graph():
    """
    Get or create the sales agent graph (singleton pattern).
    
    Returns:
        Compiled LangGraph StateGraph
    """
    global _sales_agent_graph
    
    if _sales_agent_graph is None:
        _sales_agent_graph = create_sales_agent_graph()
    
    return _sales_agent_graph


def run_conversation_turn(state: ConversationState, user_utterance: str) -> ConversationState:
    """
    Run a single turn through the LangGraph.
    
    This invokes the graph with the current state and user utterance,
    runs through all nodes according to the graph's edges,
    and returns the updated state.
    
    Args:
        state: Current conversation state
        user_utterance: What the lead just said
    
    Returns:
        Updated conversation state
    """
    print(f"[DEBUG] Starting turn with user_utterance: '{user_utterance}'")
    
    # Set the user utterance in state before running the graph
    state.current_user_utterance = user_utterance
    
    graph = get_sales_agent_graph()
    
    # Run the graph
    result_state_dict = graph.invoke(state.dict())
    
    print(f"[DEBUG] Graph completed. result_state_dict keys: {result_state_dict.keys()}")
    print(f"[DEBUG] result_state done flag: {result_state_dict.get('done', False)}")
    
    # Convert back to ConversationState
    result_state = ConversationState(**result_state_dict)
    
    # Clear the utterance for next turn
    result_state.current_user_utterance = None
    
    print(f"[DEBUG] Final state.last_agent_reply: {result_state.last_agent_reply[:100] if result_state.last_agent_reply else 'None'}...")
    print(f"[DEBUG] Final state.done: {result_state.done}")
    
    return result_state
