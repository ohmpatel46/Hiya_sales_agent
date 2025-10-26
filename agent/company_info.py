"""
Company information for Autopitch AI.

This file contains factual information about the company that can be used
by the sales agent to answer questions without hallucinating.

Agent MUST only use information from this file when answering questions.
"""

COMPANY_NAME = "Autopitch AI"

BRIEF_DESCRIPTION = "Autopitch AI is an automated sales call assistant that handles initial lead qualification, books demos, and manages follow-up communications. Our AI agent makes outbound calls on behalf of sales teams, qualifies leads in real-time, and schedules meetings directly into your calendar."

KEY_FEATURES = [
    "Automates outbound cold calls for sales teams",
    "Real-time lead qualification and conversation management",
    "Natural language understanding to detect interest, objections, and tone",
    "Direct calendar integration for demo booking",
    "Voice-powered sales assistant that saves 10-20 hours per SDR per week",
    "CRM integration to log call outcomes and schedule follow-ups"
]

USE_CASES = [
    "B2B SaaS companies with inside sales teams",
    "Sales agencies managing multiple client accounts",
    "High-volume lead qualification scenarios"
]

INTEGRATIONS = [
    "Google Calendar for meeting scheduling",
    "CRM systems (via API)",
    "Vonage for telephony infrastructure",
    "SMS/Email for follow-up communications"
]

PRICING_APPROACH = "Custom pricing based on call volume and team size. Contact us for a demo."

# Company metrics and benefits
PRODUCTIVITY_BENEFIT = "Saves sales teams 10-20 hours per week by automating the initial outreach and qualification process"
CLIENT_COUNT = "50+ B2B companies already using Autopitch"
SUCCESS_METRICS = "Teams typically see a 3x increase in qualified demo bookings and free up SDRs to focus on closing deals"

COMPANY_FACTS = {
    "name": COMPANY_NAME,
    "description": BRIEF_DESCRIPTION,
    "features": KEY_FEATURES,
    "use_cases": USE_CASES,
    "integrations": INTEGRATIONS,
    "pricing": PRICING_APPROACH,
    "productivity_benefit": PRODUCTIVITY_BENEFIT,
    "client_count": CLIENT_COUNT,
    "success_metrics": SUCCESS_METRICS
}


def get_company_info() -> dict:
    """
    Return all company information in a structured format.
    """
    return COMPANY_FACTS


def get_info_snippet_for_questions() -> str:
    """
    Return a formatted snippet of company info for LLM context.
    This is what the agent will use to answer questions.
    """
    features_str = "\n".join(f"- {f}" for f in KEY_FEATURES)
    use_cases_str = "\n".join(f"- {u}" for u in USE_CASES)
    integrations_str = "\n".join(f"- {i}" for i in INTEGRATIONS)
    
    return f"""
COMPANY: {COMPANY_NAME}

WHAT WE DO:
{BRIEF_DESCRIPTION}

KEY FEATURES:
{features_str}

WHO USES IT:
{use_cases_str}

INTEGRATIONS:
{integrations_str}

PRODUCTIVITY BENEFITS:
- {PRODUCTIVITY_BENEFIT}
- {CLIENT_COUNT}
- {SUCCESS_METRICS}

PRICING: {PRICING_APPROACH}
""".strip()

