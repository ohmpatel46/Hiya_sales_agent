"""
Path-specific nodes for LangGraph.

These nodes handle the specific paths through the conversation:
- schedule_path: Handles meeting scheduling
- send_info_path: Handles sending information
- not_interested_path: Handles polite exits
- close_out: Final cleanup

Each path node should:
- Look at the current state
- Try to move us closer to a terminal outcome
- Possibly mark state.done = True
- Possibly generate an additional follow-up line
- Append that to state.last_agent_reply or return it
- Return updated state

For now, these are stubs that don't actually call real APIs (Google Calendar, CRM).
TODO comments mark where those integrations would go.
"""

from agent.state import ConversationState
from typing import Dict, Any
from datetime import timedelta, datetime


def schedule_path_node(state: ConversationState, user_utterance: str) -> ConversationState:
    """
    Handle the scheduling path - handles different phases differently.
    
    Phases handled:
    - confirm_meeting: User gave specific time, confirm it and mark done
    - propose_meeting: Ask for meeting time (first pass)
    - reschedule: Ask for callback time  
    - propose_specific_time: Proposing a specific time based on vague input
    - clarify_time: Need more specific time info
    """
    user_lower = user_utterance.lower()
    confirmation_words = ["yes", "confirm", "sounds good", "perfect", "ok", "okay", "that works", "sure", "book it"]
    rejection_words = ["no", "not that time", "different time", "how about", "maybe"]
    
    confirmed = any(word in user_lower for word in confirmation_words)
    rejected = any(word in user_lower for word in rejection_words)
    
    print(f"[DEBUG] schedule_path_node: phase={state.phase}, datetime={state.slots.get('datetime')}, confirmed={confirmed}")
    
    # PHASE: confirm_meeting - User gave specific time, confirm it
    if state.phase == "confirm_meeting":
        print(f"[DEBUG] In confirm_meeting phase")
        if confirmed and state.slots.get("datetime"):
            # User confirmed - finalize the meeting
            state.slots["confirmation"] = True
            state.done = True
            meeting_time = state.slots["datetime"].strftime("%A, %B %d at %I:%M %p")
            
            # Create calendar event when meeting is confirmed
            try:
                from agent.tools import calendar
                
                # Calculate end time (1 hour after start)
                start_dt = state.slots["datetime"]
                end_dt = start_dt.replace(hour=start_dt.hour + 1)
                
                # Prepare attendees
                attendees = []
                if state.lead and state.lead.email:
                    attendees = [(state.lead.name, state.lead.email)]
                
                # Create calendar event
                result = calendar.create_event(
                    summary=f"Demo Call - {state.lead.name}",
                    description="AI Sales Agent Demo Call",
                    start_dt=start_dt.isoformat(),
                    end_dt=end_dt.isoformat(),
                    attendees=attendees
                )
                
                if result.get("created"):
                    print(f"[DEBUG] Calendar event created: {result.get('id')}")
                    meeting_msg = f"Perfect. Just to make sure I have it right, I've got you down for {meeting_time}. You'll receive a calendar invite shortly. Looking forward to chatting!"
                else:
                    print(f"[DEBUG] Calendar creation failed: {result.get('error')}")
                    meeting_msg = f"Perfect. Just to make sure I have it right, I've got you down for {meeting_time}. Calendar invite will be sent shortly. Looking forward to chatting!"
                
            except Exception as e:
                print(f"[DEBUG] Error creating calendar event: {e}")
                meeting_msg = f"Perfect. Just to make sure I have it right, I've got you down for {meeting_time}. Looking forward to chatting!"
            
            state.last_agent_reply = meeting_msg
            print(f"[DEBUG] Meeting confirmed with datetime: {meeting_time}")
        return state
    
    # PHASE: propose_specific_time - We proposed a specific time, wait for confirmation
    if state.phase == "propose_specific_time":
        print(f"[DEBUG] In propose_specific_time phase")
        if confirmed:
            # User confirmed the proposed specific time
            proposed_time = state.slots.get("suggested_time", "")
            from agent.date_parser import parse_sales_date
            try:
                datetime_str = parse_sales_date(proposed_time)
                if datetime_str:
                    dt = datetime.fromisoformat(datetime_str)
                    state.slots["datetime"] = dt
                    state.slots["confirmation"] = True
                    print(f"[DEBUG] Confirmed proposed time as: {dt}")
            except Exception as e:
                print(f"[DEBUG] Error parsing confirmed time: {e}")
        elif rejected:
            # User wants different time - extract from their response
            from agent.planner import extract_datetime
            extract_datetime(user_utterance, state)
        return state
    
    # PHASE: propose_meeting, reschedule, clarify_time, ask_for_clarification
    # These just pass through - the reply was already generated in bridge_and_nudge
    # They don't mark done here, wait for next user response
    
    # Check if meeting is fully confirmed and ready to finalize
    has_datetime = state.slots.get("datetime") is not None
    is_confirmed = confirmed or state.slots.get("confirmation", False)
    
    if has_datetime and is_confirmed and not state.done:
        print(f"[DEBUG] Meeting confirmed, marking done")
        state.done = True
        meeting_time = state.slots["datetime"].strftime("%A, %B %d at %I:%M %p")
        
        # Create calendar event when meeting is confirmed
        try:
            from agent.tools import calendar
            
            # Calculate end time (1 hour after start)
            start_dt = state.slots["datetime"]
            end_dt = start_dt.replace(hour=start_dt.hour + 1)
            
            # Prepare attendees
            attendees = []
            if state.lead and state.lead.email:
                attendees = [(state.lead.name, state.lead.email)]
            
            # Create calendar event
            result = calendar.create_event(
                summary=f"Demo Call - {state.lead.name}",
                description="AI Sales Agent Demo Call",
                start_dt=start_dt.isoformat(),
                end_dt=end_dt.isoformat(),
                attendees=attendees
            )
            
            if result.get("created"):
                print(f"[DEBUG] Calendar event created: {result.get('id')}")
                meeting_msg = f"\n\nPerfect. I've locked in {meeting_time}. You'll receive a calendar invite shortly!"
            else:
                print(f"[DEBUG] Calendar creation failed: {result.get('error')}")
                meeting_msg = f"\n\nPerfect. I've locked in {meeting_time}. Calendar invite will be sent shortly!"
            
        except Exception as e:
            print(f"[DEBUG] Error creating calendar event: {e}")
            meeting_msg = f"\n\nPerfect. I've locked in {meeting_time}. Calendar invite will be sent shortly!"
        
        if state.last_agent_reply:
            state.last_agent_reply += meeting_msg
        else:
            state.last_agent_reply = meeting_msg
    
    return state


def send_info_path_node(state: ConversationState, user_utterance: str) -> ConversationState:
    """
    Handle the send-info path.
    
    If we already know how to send info (sms/email) and have the address/number,
    mark state.done = True.
    Otherwise, keep asking for channel preference "text or email?"
    
    Append any additional agent line to state.last_agent_reply.
    Return updated state.
    """
    
    # Extract channel preference from user utterance
    if "channel_pref" not in state.slots:
        user_lower = user_utterance.lower()
        
        if "email" in user_lower or "@" in user_lower:
            state.slots["channel_pref"] = "email"
        elif "text" in user_lower or "sms" in user_lower:
            state.slots["channel_pref"] = "sms"
        
    # Check if we have channel preference
    if state.slots.get("channel_pref"):
        # We have a preference - send the info
        # TODO: Actually send the info via Email/SMS API here
        # if state.slots["channel_pref"] == "email":
        #     TODO: send_email(state.lead.email, ...)
        # else:
        #     TODO: send_sms(state.lead.phone, ...)
        
        channel_name = "email" if state.slots["channel_pref"] == "email" else "text"
        state.slots["info_sent"] = True
        
        # Update the reply to confirm sending and ask for follow-up meeting
        # Replace the existing reply (which was just asking for channel pref) with the confirmation + follow-up
        state.last_agent_reply = f"Perfect! I'll send you a quick summary via {channel_name}. After you review it, would you like to set up a quick 15-minute follow-up call with our team to go deeper on how this fits your needs?"
        
        # Transition to propose_meeting phase for the follow-up
        state.phase = "propose_meeting"
        print(f"[DEBUG] Info sent, transitioning to propose_meeting for follow-up call")
    
    return state


def not_interested_node(state: ConversationState, user_utterance: str) -> ConversationState:
    """
    Handle the not-interested path.
    
    Mark state.done = True and set last_agent_reply to a respectful close.
    
    Return updated state.
    """
    
    state.done = True
    
    # TODO: Log to CRM as "not_interested" outcome
    # crm_stub.log_outcome(
    #     lead=state.lead.dict(),
    #     outcome="not_interested",
    #     meta={}
    # )
    
    if state.last_agent_reply:
        state.last_agent_reply += "\n\nThanks for your time. I'll make sure we don't keep pinging you. Have a great day!"
    else:
        state.last_agent_reply = "Totally understood. I'll make sure we don't keep pinging you — thanks for the time."
    
    return state


def provide_info_node(state: ConversationState, user_utterance: str) -> ConversationState:
    """
    Handle providing company information to interested leads.
    
    This node:
    - Provides a brief 2-3 sentence overview of Autopitch AI
    - Asks if they want info PDF or to learn more now
    - Sets state.slots["info_provided"] = True
    - Doesn't mark done yet - waits for their response
    
    Return updated state.
    """
    from agent.company_info import BRIEF_DESCRIPTION
    
    # Mark that we've provided info
    state.slots["info_provided"] = True
    
    # The actual info is set by bridge_and_nudge via LLM
    # This node just tracks the state
    
    return state


def provide_more_info_node(state: ConversationState, user_utterance: str) -> ConversationState:
    """
    Handle providing MORE detailed company information.
    
    This node:
    - Provides additional details about features, use cases, integrations
    - Goes deeper than the initial brief overview
    - Sets state.slots["more_info_provided"] = True
    
    Return updated state.
    """
    state.slots["more_info_provided"] = True
    print(f"[DEBUG] Providing more detailed info")
    
    return state


def answer_question_node(state: ConversationState, user_utterance: str) -> ConversationState:
    """
    Handle answering questions using company info.
    
    This node:
    - Uses company_info to answer their question
    - Tracks questions_asked counter
    - After 2+ questions, adds a subtle nudge to meet or send PDF
    
    Return updated state.
    """
    # Track how many questions they've asked (CURRENT count, before incrementing)
    questions_asked = state.slots.get("questions_asked", 0)
    
    print(f"[DEBUG] Answering question #{questions_asked + 1}: '{user_utterance}'")
    
    # Increment the counter for next time
    state.slots["questions_asked"] = questions_asked + 1
    
    # After answering 2+ questions, add a flag to suggest meeting or PDF in the NEXT response
    if questions_asked >= 1:  # If we've answered 1+ already, this is the 2nd+ question
        state.slots["suggest_meeting_after_answer"] = True
        print(f"[DEBUG] Will suggest meeting/PDF after answering this question (question #{questions_asked + 1})")
    
    # The actual answer is set by bridge_and_nudge via LLM with company_info context
    
    return state


def close_out_node(state: ConversationState) -> ConversationState:
    """
    Final clean-up node.
    
    For the simulated call we can just leave last_agent_reply as-is.
    Only mark done if the conversation is actually complete.
    
    Return updated state.
    """
    
    # Don't automatically mark done - let the path nodes decide
    # Only mark done here if we have a confirmed meeting or graceful exit
    
    # If we got here without being marked done, it means we're still negotiating
    # So we should NOT mark done
    
    # TODO: Final CRM logging, analytics, etc.
    
    return state

