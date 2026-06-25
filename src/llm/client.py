"""
src/llm/client.py
Phase 5 — Groq LLM Client

Responsibilities:
  - Call the Groq chat completions API with a system + user prompt pair.
  - Retry on transient failures (rate limits, 5xx errors) with exponential
    backoff — max 3 attempts.
  - Raise descriptive exceptions for the caller (app.py) to handle.

Error handling matrix:
  EC-L01  GROQ_API_KEY missing          → raise RuntimeError at call time
  EC-L02  Groq RateLimitError           → retry with backoff (max 3 attempts)
  EC-L03  Groq APIStatusError (5xx)     → retry with backoff
  EC-L04  Other Groq / network errors   → raise immediately with details
  EC-L05  Empty LLM response            → raise ValueError
"""

import logging
import time

from groq import Groq, RateLimitError, APIStatusError, PermissionDeniedError, AuthenticationError

from config.settings import (
    GROQ_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)

logger = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES    = 3
_BACKOFF_BASE_S = 2.0   # seconds — doubles each retry: 2 → 4 → 8


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_groq(system_prompt: str, user_prompt: str) -> str:
    """
    Send a chat completion request to the Groq API and return the raw text.

    Parameters
    ----------
    system_prompt : str
        The system role message (persona + format instructions).
    user_prompt : str
        The user role message (preferences + candidate list).

    Returns
    -------
    str
        Raw LLM response text.

    Raises
    ------
    RuntimeError
        If GROQ_API_KEY is not configured.
    RuntimeError
        If all retry attempts fail (rate limit / server error).
    ValueError
        If the API returns an empty response.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Please add it to your .env file and restart the server."
        )

    client = Groq(api_key=GROQ_API_KEY)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.debug(
                "Groq API call — attempt %d/%d (model=%s)",
                attempt, _MAX_RETRIES, LLM_MODEL,
            )
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            content = response.choices[0].message.content

            if not content or not content.strip():
                raise ValueError("Groq returned an empty response.")

            logger.debug("Groq API call succeeded on attempt %d.", attempt)
            return content.strip()

        except (PermissionDeniedError, AuthenticationError) as exc:
            # Non-retryable: API key invalid, revoked, or network blocked
            logger.error("Groq permission/auth error (non-retryable): %s", exc)
            raise RuntimeError(
                f"Groq API access denied (HTTP 403). "
                f"This may be a network restriction, VPN issue, or invalid API key. "
                f"Original error: {exc}"
            ) from exc

        except (RateLimitError, APIStatusError) as exc:
            last_exc = exc
            wait = _BACKOFF_BASE_S ** attempt
            logger.warning(
                "Groq transient error on attempt %d/%d (%s). "
                "Retrying in %.0fs...",
                attempt, _MAX_RETRIES, type(exc).__name__, wait,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(wait)

        except ValueError:
            # Empty response — propagate immediately (no retry benefit)
            raise

        except Exception as exc:
            # Non-retryable error (auth, bad request, etc.)
            logger.error("Non-retryable Groq error: %s", exc)
            raise RuntimeError(
                f"Groq API call failed: {type(exc).__name__}: {exc}"
            ) from exc

    raise RuntimeError(
        f"Groq API call failed after {_MAX_RETRIES} attempts. "
        f"Last error: {type(last_exc).__name__}: {last_exc}"
    )
