import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import streamlit as st
import requests
import json
from typing import Dict, Any, List
import sys

# Add agent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Check if voice dependencies are available
try:
    from openai import OpenAI
    import pyaudio
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    st.warning("⚠️ Voice dependencies not installed. Run: pip install openai pyaudio")

if VOICE_AVAILABLE:
    try:
        import speech_recognition as sr
        from agent.voice_demo import speak_with_openai_tts, transcribe_audio_with_whisper_api
        
        # Initialize speech recognizer
        recognizer = sr.Recognizer()
        SR_AVAILABLE = True
    except ImportError:
        SR_AVAILABLE = False
        VOICE_AVAILABLE = False
else:
    SR_AVAILABLE = False


# API base URL
API_BASE = "http://localhost:8000"


def main():
    st.set_page_config(
        page_title="Hiya Sales Agent",
        page_icon="📞",
        layout="wide"
    )
    # Wider sidebar for leads
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { width: 420px; min-width: 420px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    st.title("📞 Hiya Sales Agent - Call Simulation")
    st.markdown("Simulate AI sales calls with lead management and Google Calendar integration")
    
    # Sidebar for lead management
    with st.sidebar:
        st.header("Lead Management")
        
        # Lead entry form
        with st.form("lead_form"):
            st.subheader("Add New Lead")
            name = st.text_input("Name", placeholder="John Doe")
            phone = st.text_input("Phone", placeholder="+1-555-123-4567")
            email = st.text_input("Email", placeholder="john@company.com")
            company = st.text_input("Company", placeholder="Acme Corp")
            notes = st.text_area("Notes", placeholder="Additional notes...")
            
            submitted = st.form_submit_button("Add Lead")
            
            if submitted and name and phone:
                try:
                    from agent.tools import crm_sheets
                    # Prefer Sheets if configured; avoid duplicates by phone
                    if crm_sheets.ensure_sheets_exist():
                        if crm_sheets.lead_exists(phone):
                            st.info("Lead already exists in Google Sheets; skipping append.")
                        else:
                            res = crm_sheets.upsert_lead(
                                phone=phone,
                                name=name,
                                email=email or None,
                                company=company or None,
                                notes=notes or None
                            )
                            if res.get("ok"):
                                st.success("Lead added to Google Sheets!")
                            else:
                                st.error(f"Sheets error: {res.get('error')}")
                        st.rerun()
                    else:
                        # Fallback to API storage
                        lead_data = {
                            "name": name,
                            "phone": phone,
                            "email": email if email else None,
                            "company": company if company else None,
                            "notes": notes if notes else None
                        }
                        response = requests.post(f"{API_BASE}/leads", json=lead_data)
                        if response.status_code == 200:
                            st.success("Lead added successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Error adding lead: {e}")
        
        # List existing leads (from Google Sheets if configured)
        st.subheader("Existing Leads")
        try:
            from agent.tools import crm_sheets
            if crm_sheets.ensure_sheets_exist():
                res = crm_sheets.list_leads(limit=100)
                if res.get("ok") and res.get("leads"):
                    for lead in res["leads"][::-1]:
                        display = f"{lead.get('name') or 'Unknown'} - {lead.get('phone')}"
                        with st.expander(display):
                            st.write(f"**Email:** {lead.get('email') or 'N/A'}")
                            st.write(f"**Company:** {lead.get('company') or 'N/A'}")
                            st.write(f"**Notes:** {lead.get('notes') or 'N/A'}")
                            # Build a compatible lead object for API calls
                            api_lead = {
                                "id": lead.get("phone", "sheet"),
                                "name": lead.get("name") or "Unknown",
                                "phone": lead.get("phone"),
                                "email": lead.get("email") or None,
                                "company": lead.get("company") or None,
                                "notes": lead.get("notes") or None,
                            }
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"📞 Simulate", key=f"sim_sheet_{lead.get('timestamp')}"):
                                    st.session_state.selected_lead = api_lead
                                    st.session_state.session_id = None
                                    st.rerun()
                            with col2:
                                if st.button(f"📱 Real Call", key=f"real_sheet_{lead.get('timestamp')}"):
                                    st.session_state.selected_lead = api_lead
                                    st.session_state.make_real_call = True
                                    st.rerun()
                else:
                    st.info("No leads found in Sheets. Add a lead above.")
            else:
                # Fallback to API storage if Sheets not configured
                response = requests.get(f"{API_BASE}/leads")
                if response.status_code == 200:
                    leads = response.json()
                    if leads:
                        for lead in leads:
                            with st.expander(f"{lead['name']} - {lead['phone']}"):
                                st.write(f"**Email:** {lead.get('email', 'N/A')}")
                                st.write(f"**Company:** {lead.get('company', 'N/A')}")
                                st.write(f"**Notes:** {lead.get('notes', 'N/A')}")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button(f"📞 Simulate", key=f"sim_{lead['id']}"):
                                        st.session_state.selected_lead = lead
                                        st.session_state.session_id = None
                                        st.rerun()
                                with col2:
                                    if st.button(f"📱 Real Call", key=f"real_{lead['id']}"):
                                        st.session_state.selected_lead = lead
                                        st.session_state.make_real_call = True
                                        st.rerun()
                    else:
                        st.info("No leads found. Add a lead above.")
                else:
                    st.error("Error loading leads")
        except Exception as e:
            st.error(f"Error loading leads: {e}")
    
    # Main conversation area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Call Simulation")
        
        # Check if we have a selected lead
        if 'selected_lead' not in st.session_state:
            st.info("👈 Select a lead from the sidebar to start a call")
            return
        
        lead = st.session_state.selected_lead
        st.write(f"**Calling:** {lead['name']} ({lead['phone']})")
        
        # Check if we should make a real call
        if st.session_state.get('make_real_call', False):
            st.warning("⚠️ **Real Call Mode** - This will make an actual phone call!")
            st.write("Make sure your Vonage credentials are configured and ngrok is running.")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📞 Make Real Call", type="primary"):
                    try:
                        response = requests.post(f"{API_BASE}/vonage/call", json={"lead": lead})
                        if response.status_code == 200:
                            data = response.json()
                            if data['success']:
                                st.success(f"✅ {data['message']}")
                                st.write(f"**Call UUID:** {data['call_uuid']}")
                                st.session_state.call_uuid = data['call_uuid']
                                st.session_state.make_real_call = False
                            else:
                                st.error(f"❌ {data['message']}")
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Error making call: {e}")
            
            with col2:
                if st.button("🔄 Back to Simulation"):
                    st.session_state.make_real_call = False
                    st.rerun()
            
            with col3:
                if st.session_state.get('call_uuid') and st.button("📴 Hang Up"):
                    try:
                        # Note: You'd need to implement a hangup endpoint
                        st.info("Hangup functionality would be implemented here")
                    except Exception as e:
                        st.error(f"Error hanging up: {e}")
            
            return
        
        # Start simulated call button
        if st.session_state.get('session_id') is None:
            if st.button("📞 Start Simulated Call", type="primary"):
                try:
                    response = requests.post(f"{API_BASE}/trigger_call", json={"lead": lead})
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.session_id = data['session_id']
                        st.session_state.conversation_history = [{
                            "role": "agent",
                            "message": data['reply'],
                            "timestamp": "now"
                        }]
                        st.rerun()
                    else:
                        st.error(f"Error starting call: {response.text}")
                except Exception as e:
                    st.error(f"Error starting call: {e}")
        else:
            # Display conversation history
            st.subheader("Conversation")
            
            for msg in st.session_state.get('conversation_history', []):
                if msg['role'] == 'agent':
                    st.markdown(f"**🤖 Agent:** {msg['message']}")
                else:
                    st.markdown(f"**👤 You:** {msg['message']}")
            
            # Check if conversation is done
            if st.session_state.get('conversation_done', False):
                st.success("✅ Call completed!")
                if st.button("Start New Call"):
                    st.session_state.session_id = None
                    st.session_state.conversation_history = []
                    st.session_state.conversation_done = False
                    st.rerun()
            else:
                # Check if we have a transcribed voice input to use
                if st.session_state.get('voice_transcript'):
                    voice_input = st.session_state.voice_transcript
                    st.session_state.voice_transcript = None  # Clear after use
                    
                    # Automatically send the voice input
                    try:
                        response = requests.post(f"{API_BASE}/simulate", json={
                            "session_id": st.session_state.session_id,
                            "lead": lead,
                            "utterance": voice_input
                        })
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Add user message to history
                            st.session_state.conversation_history.append({
                                "role": "user",
                                "message": voice_input,
                                "timestamp": "now"
                            })
                            
                            # Add agent response to history
                            st.session_state.conversation_history.append({
                                "role": "agent",
                                "message": data['reply'],
                                "timestamp": "now"
                            })
                            
                            # Check if conversation is done
                            if data['final']:
                                st.session_state.conversation_done = True
                            
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error processing voice input: {e}")
                
                # User input
                user_input = st.text_input(
                    "Your response:",
                    placeholder="Type your response here...",
                    key="user_input"
                )
                
                if st.button("Send") and user_input:
                    try:
                        response = requests.post(f"{API_BASE}/simulate", json={
                            "session_id": st.session_state.session_id,
                            "lead": lead,
                            "utterance": user_input
                        })
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Debug: Print the API response
                            st.write("**API Response Debug:**")
                            st.json({
                                "reply": data['reply'][:100] + "..." if len(data['reply']) > 100 else data['reply'],
                                "final": data.get('final', False),
                                "tool_results_count": len(data.get('tool_results', [])),
                                "state_keys": list(data.get('state', {}).keys())
                            })
                            
                            # Add user message to history
                            st.session_state.conversation_history.append({
                                "role": "user",
                                "message": user_input,
                                "timestamp": "now"
                            })
                            
                            # Add agent response to history
                            st.session_state.conversation_history.append({
                                "role": "agent",
                                "message": data['reply'],
                                "timestamp": "now"
                            })
                            
                            # Check if conversation is done
                            if data['final']:
                                st.session_state.conversation_done = True
                            
                            # Store tool results
                            if data.get('tool_results'):
                                st.session_state.tool_results = data['tool_results']
                            
                            st.rerun()
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    with col2:
        st.header("Call Details")
        
        if st.session_state.get('session_id'):
            st.write(f"**Session ID:** {st.session_state.session_id}")
            st.write(f"**Status:** {'Completed' if st.session_state.get('conversation_done') else 'Active'}")
            
            # Show tool results if any
            if st.session_state.get('tool_results'):
                st.subheader("Tool Results")
                for result in st.session_state.tool_results:
                    if result.get('created') and result.get('htmlLink'):
                        st.success("📅 Calendar event created!")
                        st.write(f"[View Event]({result['htmlLink']})")
                    elif result.get('logged'):
                        st.info("📝 CRM entry logged")
                    elif result.get('error'):
                        st.error(f"Error: {result['error']}")
        
        # Debug information
        st.subheader("Debug Info")
        if st.session_state.get('session_id'):
            st.write("**Session State:**")
            st.json({
                "session_id": st.session_state.get('session_id'),
                "conversation_done": st.session_state.get('conversation_done', False),
                "tool_results": st.session_state.get('tool_results', []),
                "conversation_history_length": len(st.session_state.get('conversation_history', []))
            })
        
        # Instructions
        st.subheader("How to Use")
        st.markdown("""
        **Simulation Mode:**
        1. **Add a Lead:** Fill out the form in the sidebar
        2. **Start Simulation:** Click "📞 Simulate" next to a lead
        3. **Respond:** Type your responses to simulate the conversation
        4. **Schedule:** The agent will try to schedule meetings in Google Calendar
        
        **Real Call Mode:**
        1. **Configure Vonage:** Set up your Vonage credentials in .env
        2. **Start ngrok:** Run `ngrok http 8000` for webhook handling
        3. **Make Real Call:** Click "📱 Real Call" next to a lead
        4. **Answer Phone:** The AI agent will call the lead's phone number
        
        **Example Responses:**
        - "Yes, I'm interested. Tomorrow at 2pm works"
        - "I'm busy right now, call me next week"
        - "Send me more information"
        - "Not interested, please remove me"
        """)


if __name__ == "__main__":
    main()
