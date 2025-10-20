"""
LangChain/LangGraph Sales Flow Implementation
Alternative workflow using industry-standard orchestration patterns
"""

from typing import Dict, Any, List, TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_community.llms import Ollama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
import json
from datetime import datetime

from agent.schemas import Lead, SessionState
from agent.tools import calendar, crm_stub


class SalesState(TypedDict):
    """State for LangGraph sales conversation"""
    messages: Annotated[List, add_messages]
    lead: Lead
    session_id: str
    slots: Dict[str, Any]
    done: bool


# Define tools for LangChain
@tool
def schedule_meeting(time_str: str, lead_name: str, lead_email: str = None) -> Dict[str, Any]:
    """Schedule a meeting with the lead"""
    from agent.date_parser import parse_sales_date
    
    parsed_time = parse_sales_date(time_str)
    if not parsed_time:
        return {"error": "Could not parse time", "success": False}
    
    # Calculate end time (1 hour later)
    start_dt = datetime.fromisoformat(parsed_time)
    end_dt = start_dt.replace(hour=start_dt.hour + 1)
    
    attendees = []
    if lead_email:
        attendees = [(lead_name, lead_email)]
    
    result = calendar.create_event(
        summary=f"Demo Call - {lead_name}",
        description="AI Sales Agent Demo Call",
        start_dt=parsed_time,
        end_dt=end_dt.isoformat(),
        attendees=attendees
    )
    
    return result


@tool
def log_call_outcome(lead_data: Dict[str, Any], outcome: str, notes: str = "") -> Dict[str, Any]:
    """Log the outcome of a sales call"""
    return crm_stub.log_outcome(lead_data, outcome, notes)


@tool
def log_followup(lead_data: Dict[str, Any], when: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Log a follow-up call"""
    return crm_stub.log_followup(lead_data, when, meta)


def create_sales_agent():
    """Create LangGraph sales agent"""
    
    # Initialize LLM
    llm = Ollama(model="llama3.2:3b", base_url="http://localhost:11434")
    
    # Define tools
    tools = [schedule_meeting, log_call_outcome, log_followup]
    tool_node = ToolNode(tools)
    
    def sales_agent(state: SalesState) -> Dict[str, Any]:
        """Main sales agent node"""
        messages = state["messages"]
        lead = state["lead"]
        
        # Create system prompt
        system_prompt = f"""You are a professional sales agent calling {lead.name} about TopSales, an AI-based lead generator.

Your goals:
1. Introduce TopSales and its benefits
2. Qualify the lead's interest
3. Schedule a demo call if interested
4. Handle objections professionally
5. End the call politely if not interested

Lead information:
- Name: {lead.name}
- Phone: {lead.phone}
- Email: {lead.email or 'Not provided'}
- Company: {lead.company or 'Not provided'}

Be conversational, professional, and focus on value. Use the available tools to schedule meetings and log outcomes."""

        # Get LLM response
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": messages[-1].content if messages else "Start the conversation"}
        ])
        
        return {"messages": [AIMessage(content=response)]}
    
    def should_continue(state: SalesState) -> str:
        """Determine if conversation should continue"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Check if agent said goodbye or call is complete
        if any(word in last_message.content.lower() for word in ["goodbye", "thank you", "have a great day"]):
            return "end"
        
        # Check if meeting was scheduled
        if "scheduled" in last_message.content.lower() or "calendar" in last_message.content.lower():
            return "end"
        
        return "continue"
    
    # Build the graph
    workflow = StateGraph(SalesState)
    
    # Add nodes
    workflow.add_node("agent", sales_agent)
    workflow.add_node("tools", tool_node)
    
    # Add edges
    workflow.add_edge("tools", "agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": END
        }
    )
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    return workflow.compile()


def run_langchain_conversation(session_id: str, lead: Lead, user_input: str) -> Dict[str, Any]:
    """Run conversation using LangChain/LangGraph"""
    
    # Create agent
    agent = create_sales_agent()
    
    # Initialize state
    initial_state = SalesState(
        messages=[HumanMessage(content=user_input)],
        lead=lead,
        session_id=session_id,
        slots={},
        done=False
    )
    
    # Run conversation
    result = agent.invoke(initial_state)
    
    # Extract final message
    final_message = result["messages"][-1].content if result["messages"] else "I apologize, but I'm having technical difficulties."
    
    return {
        "reply": final_message,
        "state": result,
        "tool_results": [],
        "final": result.get("done", False)
    }


# Example usage
if __name__ == "__main__":
    # Test the LangChain flow
    test_lead = Lead(
        id="test",
        name="John Doe",
        phone="+1234567890",
        email="john@example.com",
        company="Test Corp"
    )
    
    result = run_langchain_conversation("test_session", test_lead, "Hello, I'm interested in learning more")
    print("LangChain Response:", result["reply"])
