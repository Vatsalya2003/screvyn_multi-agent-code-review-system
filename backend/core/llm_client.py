"""
LLM client — thin wrapper around the Gemini API.
This is the ONLY file that talks to Gemini directly.
"""

import json
import logging
import re
import time

import google.generativeai as genai

from core.config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)
MODEL_NAME = settings.gemini_model


def _extract_json(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not extract JSON from LLM response. "
        f"First 200 chars: {text[:200]}"
    )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 2,
    temperature: float = 0.1,
) -> dict:
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=4096,
        ),
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            response = model.generate_content(user_prompt)
            elapsed = time.time() - start_time
            logger.info(
                "Gemini call completed in %.1fs (attempt %d/%d)",
                elapsed, attempt + 1, max_retries + 1,
            )

            if not response.text:
                raise ValueError("Gemini returned empty response")

            return _extract_json(response.text)

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning("JSON parse failed (attempt %d): %s", attempt + 1, str(e)[:100])
            if attempt < max_retries:
                time.sleep(1)
                continue

        except Exception as e:
            last_error = e
            logger.error("Gemini API error (attempt %d): %s", attempt + 1, str(e)[:100])
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue

    raise ValueError(
        f"Failed after {max_retries + 1} attempts. Last error: {last_error}"
    )
