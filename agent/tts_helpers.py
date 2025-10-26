"""
TTS helpers for natural speech generation with OpenAI TTS.
"""

import re


def add_natural_pauses(text: str) -> str:
    """
    Add natural pauses to text for more natural-sounding speech.
    
    OpenAI TTS doesn't support SSML, but punctuation creates pauses.
    We add strategic punctuation to make speech sound more conversational.
    
    Uses periods and commas strategically to add pauses.
    """
    
    # Add pauses after common conversation starters (replace with comma)
    pause_after = [
        (r'\b(right|alright|okay|sure)\b[,:]\s*', r'\1, '),
        (r'\b(yeah,?\s+so|well,?\s+so|so)\b\s+', r'\1, '),
    ]
    
    for pattern, replacement in pause_after:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Add ellipsis for thoughtful pauses (TTS will pause slightly)
    thoughtful = [
        (r'\b(hmm|well|let me think|you know)\b', r'\1...'),
    ]
    
    for pattern, replacement in thoughtful:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text


def clean_for_tts(text: str) -> str:
    """
    Clean text for TTS:
    - Remove markdown formatting
    - Fix common transcription issues
    - Add appropriate punctuation for natural pauses
    """
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # *italic*
    
    # Remove quotes at start/end
    text = text.strip('"\'')
    
    # Ensure sentences end with proper punctuation
    if text and text[-1] not in '.!?':
        text += '.'
    
    return text.strip()


def prepare_text_for_speech(text: str, add_pauses: bool = True) -> str:
    """
    Prepare text for natural-sounding TTS.
    
    Args:
        text: Raw text to speak
        add_pauses: Whether to add natural pauses
    
    Returns:
        Text ready for TTS API
    """
    # Clean first
    text = clean_for_tts(text)
    
    # Add natural pauses if requested
    if add_pauses:
        text = add_natural_pauses(text)
    
    return text


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_texts = [
        "Right, so here's how it works.",
        "Yeah, I totally get that.",
        "Alright, let me explain.",
        "So, Autopitch AI helps sales teams automate their outreach.",
    ]
    
    print("Testing natural pause insertion:")
    for text in test_texts:
        output = add_natural_pauses(text)
        print(f"Input:  {text}")
        print(f"Output: {output}")
        print()

