"""
LangChain helpers for intent classification, tone detection, and reply generation.

This module uses LangChain to:
1. Classify user intent (interested/busy/send_info/etc.)
2. Detect conversational tone (friendly/rushed/skeptical/etc.)
3. Generate human-sounding agent replies that match tone and drive toward goals

The LLM is ONLY responsible for phrasing and tone - not business strategy.
Business strategy is determined by planner.py (deterministic Python logic).
"""

import os
from typing import Dict, Any, Optional
import re
from agent.state import ConversationState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Try to import OpenAI
try:
    from langchain_openai import ChatOpenAI
    USE_LLM = True
    print("[INFO] Using OpenAI for LLM")
except ImportError:
    USE_LLM = False
    print("ERROR: langchain-openai not available. Install with: pip install langchain-openai")


def _get_llm():
    """
    Get LLM instance - OpenAI GPT.
    
    Requires OPENAI_API_KEY environment variable.
    """
    if not USE_LLM:
        print("[ERROR] langchain-openai not installed")
        return None
    
    try:
        from langchain_openai import ChatOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[ERROR] OPENAI_API_KEY environment variable not set!")
            print("[ERROR] Add it to your .env file or export it")
            return None
        
        return ChatOpenAI(
            model="gpt-4o-mini",  # Fast and cost-effective
            temperature=0.7,
            max_tokens=200
        )
    except Exception as e:
        print(f"[ERROR] Failed to initialize OpenAI LLM: {e}")
        return None


def classify_intent_chain(user_utterance: str) -> Dict[str, Any]:
    """
    Classify user intent using heuristics + LangChain LLM fallback.
    
    Returns:
        {
            "intent": "interested" | "busy" | "send_info" | "not_interested" | "question" | "unclear",
            "confidence": float  # 0.0 to 1.0
        }
    """
    user_lower = user_utterance.lower().strip()
    
    # Print debug info
    print(f"[DEBUG] Classifying intent for: '{user_utterance}'")
    
    # Use LLM for intent classification (more flexible and natural)
    llm = _get_llm()
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are analyzing a sales phone call. Classify what the person said into ONE of these intents based on their words and context:

INTENTS:
1. interested - They want to continue, are available, show interest. Examples: "yes", "sure", "i got time", "lets do it", "sounds good", "tell me more", "i'm interested"
2. busy - They explicitly say they're busy/occupied/can't talk NOW. Examples: "i'm busy", "not a good time", "in a meeting", "can't talk", "got my hands full"
3. send_info - They want info sent (email/SMS/PDF). Examples: "send me", "email me", "text me the pdf", "can you send"
4. not_interested - They reject/reject. Examples: "not interested", "no thanks", "remove me", "never call again"
5. question - They ask about product/service. Examples: "does it", "how does", "what about", "can you explain", "does it integrate"
6. unclear - Can't determine intent. Examples: "hmm", "maybe", "i don't know"

The examples are just examples - you must classify the intent based on the user's words and context.

CONTEXT RULES:
- If they say they have TIME/AVAILABILITY → INTERESTED (not busy)
- If they explicitly say BUSY/CANT TALK NOW → BUSY
- Short responses like "yes", "sure", "okay" → INTERESTED
- Asking "what is this" or "how does" → QUESTION
- "lets schedule" or "lets do" → INTERESTED

Respond with ONLY this JSON format: {{"intent": "interested", "confidence": 0.9}}
Set confidence based on how clear the intent is (0.8-1.0 for clear, 0.3-0.7 for ambiguous).
"""),
                ("user", "Classify this: {user_input}")
            ])
            
            chain = prompt | llm | StrOutputParser()
            response = chain.invoke({"user_input": user_utterance})
            
            # Parse JSON response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                import json
                result = json.loads(json_match.group())
                print(f"[DEBUG] Classified as: {result}")
                return result
        except Exception as e:
            print(f"LLM intent classification error: {e}")
    
    # Default fallback
    fallback = {"intent": "unclear", "confidence": 0.5}
    print(f"[DEBUG] Classified as (fallback): {fallback}")
    return fallback


def detect_tone_chain(user_utterance: str) -> tuple[str, float]:
    """
    Detect conversational tone using heuristics + optional LangChain.
    
    Returns:
        tuple of (tone: str, confidence: float)
    """
    user_lower = user_utterance.lower().strip()
    
    # Heuristic tone detection (fast)
    # Count how many indicators match - higher count = higher confidence
    shut_down_indicators = ["no", "stop", "not interested", "remove", "don't"]
    rushed_indicators = ["busy", "meeting", "hurry", "quick", "can't talk", "not a good time"]
    skeptical_indicators = ["robocall", "scam", "spam", "sure about", "how do you", "is this"]
    curious_indicators = ["?", "how", "what", "why", "explain", "tell me"]
    friendly_indicators = ["sure", "yes", "interested", "sounds good", "alright", "okay"]
    
    # Count matches for each tone
    shut_down_matches = sum(1 for word in shut_down_indicators if word in user_lower)
    rushed_matches = sum(1 for word in rushed_indicators if word in user_lower)
    skeptical_matches = sum(1 for word in skeptical_indicators if word in user_lower)
    curious_matches = sum(1 for word in curious_indicators if word in user_lower)
    friendly_matches = sum(1 for word in friendly_indicators if word in user_lower)
    
    # Determine tone and confidence based on matches
    if shut_down_matches > 0:
        confidence = min(0.9, 0.7 + (shut_down_matches * 0.1))
        return ("shut_down", confidence)
    elif rushed_matches > 0:
        confidence = min(0.9, 0.7 + (rushed_matches * 0.1))
        return ("rushed", confidence)
    elif skeptical_matches > 0:
        confidence = min(0.9, 0.7 + (skeptical_matches * 0.1))
        return ("skeptical", confidence)
    elif curious_matches > 0:
        confidence = min(0.85, 0.6 + (curious_matches * 0.1))
        return ("curious", confidence)
    elif friendly_matches > 0:
        confidence = min(0.9, 0.8 + (friendly_matches * 0.05))
        return ("friendly", confidence)
    else:
        # Default to friendly if no strong indicators
        return ("friendly", 0.6)
    
    # TODO: Could add LangChain fallback for ambiguous cases


def explain_path_goal(next_action: str) -> str:
    """Explain what this path is trying to achieve"""
    goals = {
        "confirm_meeting": "Confirm the specific time they provided and book the meeting",
        "propose_meeting": "Get them excited and commit to a demo time",
        "reschedule": "Book a callback when they're available",
        "propose_specific_time": "Get confirmation on a specific time slot",
        "provide_info": "Give them a brief overview of Autopitch and ask if they want info PDF or to learn more now",
        "provide_more_info": "Give them additional detailed information about features, use cases, and integrations that wasn't covered initially",
        "answer_question": "Answer their specific question using factual company information",
        "ask_channel_pref": "Get their preferred contact method to send info",
        "graceful_exit": "End the call respectfully and ensure no follow-ups",
        "clarify_time": "Get more specific time information",
        "ask_for_clarification": "Understand what they want"
    }
    return goals.get(next_action, "Have a productive conversation")


def explain_path_context(next_action: str, state: ConversationState) -> str:
    """Explain the context for this path"""
    if next_action == "confirm_meeting":
        dt = state.slots.get("datetime")
        if dt:
            formatted = dt.strftime("%A at %I:%M %p")
            return f"Lead provided specific time: {formatted}. Confirm it with them."
        return "Need to confirm the meeting time"
    elif next_action == "propose_meeting":
        return "Lead is interested in learning more about Autopitch AI"
    elif next_action == "reschedule":
        return "Lead is busy right now but might be interested later"
    elif next_action == "propose_specific_time":
        suggested = state.slots.get("suggested_time", "a time")
        return f"Lead gave vague time reference, proposing: {suggested}"
    elif next_action == "ask_channel_pref":
        return "Lead wants information sent to them"
    elif next_action == "provide_info":
        from agent.company_info import BRIEF_DESCRIPTION
        is_intro = state.phase == "intro"
        if is_intro:
            return f"Lead is asking who you are - introduce yourself as an AI sales agent for Autopitch AI, then give 2-3 sentences about what Autopitch does, then offer: chat now or send PDF + schedule later."
        return f"Lead is interested - give them 1-2 sentences: {BRIEF_DESCRIPTION}. Then offer: chat now or send PDF + schedule later."
    elif next_action == "provide_more_info":
        from agent.company_info import KEY_FEATURES, USE_CASES
        # Give them more details about features and use cases that wasn't in the initial brief
        features_snippet = "; ".join(KEY_FEATURES[:3])  # First 3 features
        use_cases_snippet = "; ".join(USE_CASES[:2])    # First 2 use cases
        return f"Lead wants MORE details. Give them specifics: {features_snippet}. Use cases: {use_cases_snippet}. Then ask if they want a PDF or to continue talking."
    elif next_action == "answer_question":
        questions = state.slots.get("questions_asked", 0)
        if questions >= 1:
            return f"Lead has asked {questions} question(s) - if they ask more, pivot to meeting proposal"
        return "Lead wants to know more - answer their question using company facts from the info provided"
    elif next_action == "graceful_exit":
        return "Lead is not interested, need to exit gracefully"
    else:
        return "Need to move the conversation forward"


def get_tone_style_guide(tone: str) -> str:
    """Get style guide for a given tone"""
    guides = {
        "friendly": "Be warm and natural. Vary your acknowledgments - don't always say 'Awesome!'. Use: 'Got it', 'Sure thing', 'Perfect', 'That works'",
        "rushed": "Be SUPER concise, no fluff. Get to the point immediately. Use: 'Got it', 'Quick question'",
        "skeptical": "Be reassuring, low-pressure, professional. Use: 'Totally understand', 'Just to be clear'",
        "shut_down": "Be brief, respectful, make it easy to exit. Use: 'No problem', 'Understood'",
        "curious": "Be helpful and informative. Answer directly, don't over-explain. Use: 'Sure', 'Got it', 'Yep'",
    }
    return guides.get(tone, "Be professional and friendly")


def generate_reply_chain(state: ConversationState, user_utterance: str, next_action: str) -> str:
    """
    Generate agent reply using LangChain LLM.
    
    This is where LangChain is ACTUALLY used for generation.
    The prompt enforces:
    1. Acknowledge what lead just said
    2. Match their tone (rushed = concise, skeptical = reassure, friendly = warm, etc.)
    3. End with CTA that supports next_action
    
    Args:
        state: Current conversation state with intent, tone, lead info
        user_utterance: What the lead just said
        next_action: Business strategy from planner.py (propose_meeting, reschedule, etc.)
    
    Returns:
        Agent reply string
    """
    print(f"[DEBUG] generate_reply_chain: next_action={next_action}, user said: '{user_utterance}'")
    
    # Map next_action to CTAs (conditional on what we know)
    has_datetime = state.slots.get("datetime") is not None
    
    if has_datetime:
        # We have a specific datetime - ask for confirmation
        dt = state.slots["datetime"]
        formatted_time = dt.strftime("%A at %I:%M %p")
        cta = f"Perfect! {formatted_time} works. Shall I book it?"
    elif state.slots.get("suggested_time"):
        # We have a vague time, proposed a specific one
        suggested = state.slots.get("suggested_time", "tomorrow at 2pm")
        cta = f"How about {suggested}?"
    else:
        # No time info - ask for time
        cta_map = {
            "propose_meeting": "When's a good 15-minute window, later today or tomorrow?",
            "reschedule": "When should I call you back? Later today or tomorrow morning?",
            "provide_info": "If you're not too busy, we can chat right now, or I can send you a PDF you can review and we can schedule a follow-up at your convenience?",
            "provide_more_info": "Let me give you a quick overview of the key features. Would you like to learn more, or I can send you a detailed PDF?",
            "answer_question": "",  # No CTA for first questions - let it flow naturally
            "ask_channel_pref": "Should I send a quick summary by text or email?",
            "clarify_time": "Just so I block the right time, what exact time works for you?",
            "graceful_exit": "I'll make sure we don't keep pinging you — thanks for the time.",
            "ask_for_clarification": "Would you rather I send a quick summary, or do a quick walkthrough?"
        }
        cta = cta_map.get(next_action, "Thanks for your time.")
        
        # Special case: if answer_question and we should suggest meeting after 2+ questions
        # Note: questions_asked is the CURRENT count (not yet incremented by answer_question_node)
        # So we check >= 1 to trigger on the 2nd question (after 1st question answered)
        questions_asked = state.slots.get("questions_asked", 0)
        if next_action == "answer_question":
            if questions_asked >= 1:  # If we've answered 1+ questions, this will be the 2nd+
                cta = "I can send you a detailed PDF to review, or we can set up a quick 15-min call with our team - which works better for you?"
                print(f"[DEBUG] Questions asked: {questions_asked}, adding CTA to suggest meeting/PDF")
            else:
                cta = ""  # No CTA for first question - let conversation flow naturally
                print(f"[DEBUG] First question, no CTA yet")
    
    # Tone adaptation instructions
    tone_adapt = {
        "friendly": "Be warm and conversational",
        "rushed": "Be super concise and respectful of their time",
        "skeptical": "Reassure them this is legitimate and low-pressure",
        "shut_down": "Be brief, respectful, and make it easy for them to exit",
        "curious": "Be helpful and informative"
    }
    tone_instruction = tone_adapt.get(state.tone or "friendly", "Be professional")
    
    # Build context from conversation history
    history_context = ""
    if state.conversation_history:
        recent_turns = state.conversation_history[-2:]  # Last 2 turns for context
        history_context = "\n\nRECENT CONVERSATION:\n"
        for turn in recent_turns:
            history_context += f"Turn {turn['turn']}: Lead said '{turn['user']}'\n"
            history_context += f"Agent replied: '{turn['agent']}'\n"
    
    # Load company info if needed for provide_info or answer_question
    company_info_snippet = ""
    if next_action in ["provide_info", "answer_question", "provide_more_info"]:
        from agent.company_info import get_info_snippet_for_questions
        company_info_snippet = get_info_snippet_for_questions()
    
    # Get context from helpers
    goal = explain_path_goal(next_action)
    context = explain_path_context(next_action, state)
    style_guide = get_tone_style_guide(state.tone or "friendly")
    
    # Build prompt with optional company info
    company_info_section = ""
    if company_info_snippet:
        company_info_section = f"\nCOMPANY INFORMATION (USE ONLY THIS):\n{company_info_snippet}\n"
    
    # Build different prompts based on action
    if next_action == "provide_info":
        is_intro = state.phase == "intro"
        if is_intro:
            system_prompt = f"""You are a REAL SALES AGENT on the phone with {state.lead.name}, a real potential customer. This is a LIVE sales call.

WHAT JUST HAPPENED:
They said: "{user_utterance}" - they're asking who you are

YOUR COMPANY INFORMATION:
{company_info_section}

YOUR MISSION:
You are talking to a REAL person on the phone right now. Introduce yourself and explain what Autopitch does, then offer to chat now or send info. Be natural and conversational.

RESPONSE STRUCTURE:
1. Tell them who you are: "Hi, I'm an AI sales agent for Autopitch AI."
2. Explain what Autopitch does: 2-3 sentences from the company info
3. End with: {cta}

EXAMPLE:
"Hi, I'm an AI sales agent for Autopitch AI. We help sales teams automate their outbound calling by making AI agents that qualify leads, book demos, and handle follow-ups - basically do the initial outreach so your team can focus on closing deals. If you're not too busy, we can chat right now, or I can send you a PDF you can review and we can schedule a follow-up at your convenience?"

CRITICAL: You are talking to a REAL PERSON ON THE PHONE. Do NOT output meta-commentary, instructions to yourself, or notes. Just have the natural conversation.

OUTPUT 2-3 complete sentences."""
        else:
            system_prompt = f"""You are a sales person calling {state.lead.name} about Autopitch AI.

WHAT JUST HAPPENED:
They said: "{user_utterance}" - they're interested and want to know more

YOUR COMPANY INFORMATION:
{company_info_section}

YOUR MISSION:
Give them 2-3 sentences about what Autopitch does (USE THE COMPANY INFO ABOVE), then ask the question.

RESPONSE STRUCTURE:
1. Friendly acknowledgment (example: "Awesome", "Perfect")  
2. 2-3 sentences about what Autopitch does (from the info above)
3. End with: {cta}

EXAMPLE:
"Awesome! Autopitch AI is an automated sales call assistant that handles initial lead qualification, books demos, and manages follow-up communications. Our AI agent makes outbound calls on behalf of sales teams, qualifies leads in real-time, and schedules meetings directly into your calendar. If you're not too busy, we can chat right now, or I can send you a PDF you can review and we can schedule a follow-up at your convenience?"

OUTPUT 2-3 complete sentences."""
    elif next_action == "answer_question":
        system_prompt = f"""You are on a LIVE phone call with {state.lead.name}. They just asked you: "{user_utterance}"

BELOW IS THE COMPANY INFO - USE IT TO ANSWER:
{company_info_section}

YOUR JOB:
Find the answer in the company info above and give it to them naturally, like a real person answering their question.

SPECIFIC INSTRUCTIONS:
- Look at the INTEGRATIONS section for CRM questions
- Look at the KEY FEATURES section for feature questions  
- Look at the PRICING section for cost questions
- Answer directly from the info above
- Be conversational and natural
- Optional: Add this if relevant: {cta}

FOR CRM QUESTIONS:
If they ask about CRM integration, look in the INTEGRATIONS section above and answer based on that.

EXAMPLE RESPONSES:
Input: "Does it integrate with CRM?"
Output: "Yes, absolutely! We integrate with all major CRM systems via API."

Input: "What does it do?"
Output: "Autopitch AI automates outbound sales calls, qualifies leads, and books demos for sales teams. Our AI agent handles the initial outreach so your team can focus on closing deals."

Input: "How much?"
Output: "We do custom pricing based on your call volume and team size."

NEVER SAY THESE (wrong):
❌ "I'd say, 'Let Autopitch...'"  
❌ "Let me schedule a demo..."
❌ "Here's how it works..."
❌ "Let me provide you..."

INSTEAD SAY (right):
✅ Direct answer from company info
✅ Natural, conversational response
✅ Just the facts

They asked: "{user_utterance}"
Find the answer in the company info above and respond naturally.
"""
    elif next_action == "provide_more_info":
        from agent.company_info import KEY_FEATURES, USE_CASES, PRODUCTIVITY_BENEFIT, CLIENT_COUNT, SUCCESS_METRICS
        features_snippet = "\n".join([f"- {f}" for f in KEY_FEATURES[:4]])  # First 4 features
        use_cases_snippet = "\n".join([f"- {uc}" for uc in USE_CASES[:2]])  # First 2 use cases
        system_prompt = f"""You are a sales person calling {state.lead.name} about Autopitch AI.

WHAT JUST HAPPENED:
They said: "{user_utterance}" - they want MORE details about how Autopitch makes sales teams more productive

ADDITIONAL COMPANY INFORMATION:
KEY FEATURES:
{features_snippet}

USE CASES:
{use_cases_snippet}

PRODUCTIVITY BENEFITS:
- {PRODUCTIVITY_BENEFIT}
- {CLIENT_COUNT}
- {SUCCESS_METRICS}

YOUR MISSION:
Give them 3-4 sentences covering:
1. How it makes sales teams' lives easier (productivity benefits)
2. Who uses it (use cases)
3. Results/metrics (client count, success metrics)
Then ask if they want a PDF or to continue talking.

CRITICAL RULES:
1. Emphasize how it SAVES TIME and makes their life EASIER
2. Mention the client count to build credibility
3. Keep it conversational and natural
4. End with: {cta}

DON'T SAY:
- "Here are 3-4 sentences..." ❌
- "Here's a possible response..." ❌
- "Example:" ❌
- Any meta-commentary ❌

SAY INSTEAD (actual conversational response):
"Perfect! Autopitch automates all the cold calling and lead qualification so your team can focus on closing deals. We've got 50+ companies using it already - most see a 3x increase in qualified demos. The real win is that your SDRs save 10-20 hours per week because our AI handles the initial outreach and booking. Would you like to keep chatting, or should I send you a detailed PDF to review?"

OUTPUT: ONLY the actual conversational response, nothing else."""
    else:
        system_prompt = f"""You are a sales person calling {state.lead.name} about Autopitch AI.

WHAT JUST HAPPENED:
They said: "{user_utterance}"
Their energy/tone: {state.tone} (match this style)
{context}
{company_info_section}YOUR MISSION:
Path: {next_action}
Goal: {goal}
Must end with: {cta}

HOW TO TALK (match their energy):
{style_guide}

STRUCTURE YOUR RESPONSE:
1. ONE friendly acknowledgment word (from the style guide above)
2. Brief mention of what Autopitch does (automates sales calls, qualifies leads, books demos)
3. The exact question shown above

CRITICAL - DON'T SAY:
- "I'd be happy to..." ❌
- "Can you tell me more..." ❌  
- Asking them to explain their interest ❌
- Meta-commentary about helping ❌

SAY INSTEAD (examples of style):
- They're interested: "That sounds great! When's a good time for a quick 15-minute chat?"
- They're busy: "No problem, should I call you back later today or tomorrow morning?"
- They're skeptical: "Totally get it. When might be a better time to connect?"

CRITICAL:
- You are talking to a REAL PERSON on the phone RIGHT NOW
- This is a LIVE sales call happening in real-time
- Do NOT output meta-commentary like "Here's a possible response..." or "Example:"
- Be conversational and natural
- End with: {cta}

Example good outputs:
"Perfect! When's a good 15-minute window?"
"Got it. What time works better for you?"
"Sounds good, should I try you later today or tomorrow?"

DO NOT be repetitive or robotic. DO NOT output notes, instructions, or meta-commentary. Just have the natural conversation.
"""

    llm = _get_llm()
    
    if llm:
        try:
            # Use LangChain to generate reply
            user_prompt = "What would you say?" if next_action == "provide_info" else "What one sentence would you say to book the meeting?"
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", user_prompt)
            ])
            
            chain = prompt | llm | StrOutputParser()
            reply = chain.invoke({})
            
            # Clean up the reply - remove quotes, strip whitespace
            reply = reply.strip().strip('"').strip("'")
            
            # Remove any markdown formatting or meta-commentary that might slip through
            reply = reply.replace("**", "").strip()
            
            # Extract just the first sentence if LLM generated multiple (except for provide_info which needs 2-3 sentences)
            if "\n" in reply:
                reply = reply.split("\n")[0]
            if next_action != "provide_info" and "." in reply and len(reply.split(".")) > 2:
                # Take first sentence if too long (but not for provide_info)
                sentences = reply.split(".")
                reply = sentences[0] + "."
            
            print(f"[DEBUG] LLM generated reply: {reply}")
            
            # Check if LLM generated meta-commentary OR incomplete response
            meta_indicators = ["i'd be happy", "can you tell me more", "i'd like to", "let me help"]
            is_meta = any(phrase in reply.lower() for phrase in meta_indicators)
            
            # Check if reply is too short (missing description or CTA)
            # provide_info needs 2+ sentences, answer_question can be 1 sentence
            num_sentences = len([s for s in reply.split(".") if s.strip()])
            min_sentences = 3 if next_action == "provide_info" else 1  # provide_info needs 2-3, answer_question just needs 1+
            is_too_short = num_sentences < min_sentences
            missing_cta = cta.lower() not in reply.lower()  # Check if CTA is missing for any action
            
            # Check for bad/meta responses
            bad_responses = [
                "sorry, i can't", "can't fulfill", "according to the information", "it's actually not possible",
                "here are", "here's a possible", "example:", "would be:", "could be:", "should be:"
            ]
            is_bad_response = any(bad in reply.lower() for bad in bad_responses)
            
            # If LLM generated bad/meta response or too short, just regenerate with tighter prompt
            if is_bad_response or is_meta or (is_too_short and not missing_cta):
                print(f"[DEBUG] LLM generated {'bad response' if is_bad_response else 'meta-commentary' if is_meta else 'too short'}: '{reply}'")
                print(f"[DEBUG] Returning as-is (OpenAI should handle CTA in prompt)")
                # Don't fallback - just return what we have and let OpenAI figure it out
            
            # If LLM generated good content but missing CTA, append it
            if missing_cta:
                reply = f"{reply} {cta}"
                print(f"[DEBUG] Appended CTA to LLM response: {cta}")
            
            return reply
            
        except Exception as e:
            print(f"LLM reply generation error: {e}")
            # Fallback to template-based reply
            pass
    
    # Fallback: template-based reply (used if LLM unavailable)
    print(f"[DEBUG] Using template fallback for next_action: {next_action}")
    return _generate_template_reply(state, user_utterance, next_action, cta)


def _generate_template_reply(state: ConversationState, user_utterance: str, next_action: str, cta: str) -> str:
    """Template fallback when LLM is unavailable - ONE natural sentence"""
    
    # ONE friendly word
    friendly_words = ["Awesome", "Perfect", "Got it", "Alright"]
    acknowledgment = friendly_words[0]  # Default to first one
    
    # Brief description of what we do
    description = "We help automate your sales calls and book demos automatically"
    
    # Build ONE natural sentence
    if next_action in ["propose_meeting", "reschedule"]:
        return f"{acknowledgment}! {description}. {cta}"
    elif next_action == "ask_channel_pref":
        return f"{acknowledgment}. {cta}"
    else:
        return f"{acknowledgment}. {cta}"

