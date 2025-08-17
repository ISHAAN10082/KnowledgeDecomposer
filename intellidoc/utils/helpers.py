import json
import re
from typing import Any
from intellidoc.config import settings
from intellidoc.models.ollama_client import OllamaClient

def llm_json_sanitizer(text: str) -> str:
    """
    Uses a fast, secondary LLM to extract a clean JSON string from a potentially messy output.
    This is the most robust method for handling unpredictable LLM responses.
    """
    try:
        cleaner_prompt = (
            "You are an expert JSON cleaning utility. Your sole task is to extract a valid, "
            "parseable JSON array from the provided text. Respond with ONLY the JSON array and nothing else. "
            "If no valid JSON array is found, return an empty array '[]'.\n\n"
            f"Text to clean:\n---\n{text}\n---\nValid JSON array:"
        )
        # Use the fast validation model for this task
        cleaner_llm = OllamaClient(settings.models.validation_model)
        cleaned_text = cleaner_llm.generate(cleaner_prompt)
        return cleaned_text
    except Exception as e:
        print(f"LLM JSON sanitizer failed: {e}")
        return text # Fallback to original text

def robust_json_load(text: str) -> Any:
    """
    Attempts to parse a JSON object from a string, using an LLM-based sanitizer as the primary method.
    """
    # First, try a direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass # Fall through to sanitization

    # If direct parse fails, use the LLM sanitizer
    sanitized_text = llm_json_sanitizer(text)
    
    try:
        return json.loads(sanitized_text)
    except json.JSONDecodeError:
        # As a last resort, try to find the outermost JSON structure in the sanitized text
        # This can help if the sanitizer still leaves some minor whitespace or a single trailing character
        start_bracket = sanitized_text.find('[')
        end_bracket = sanitized_text.rfind(']')
        if start_bracket != -1 and end_bracket != -1:
            json_str = sanitized_text[start_bracket:end_bracket+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    return None # Indicate final failure 