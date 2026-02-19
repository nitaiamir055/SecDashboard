"""SLM integration via Ollama: sends structured prompts and parses
JSON responses for each filing segment type."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx

from ..config import get_settings

log = logging.getLogger("secpulse.ai")

PROMPT_DIR = Path(__file__).parent.parent / "prompts"

_CHUNK_WORD_SIZE = 8000  # words per chunk


def _load_prompt(segment: str) -> str:
    """Load the prompt template for the given segment."""
    path = PROMPT_DIR / f"{segment}.txt"
    if path.exists():
        return path.read_text()
    return _DEFAULT_PROMPT


_DEFAULT_PROMPT = """You are a financial analyst. Analyze this SEC filing and provide a brief assessment.

Company: {company} ({ticker})
Form: {form_type}

Structured data:
{parsed_data}

Filing excerpt:
{raw_text}

Respond in EXACTLY this JSON format:
{{"summary": "<2-3 sentence summary>", "impact": <integer -100 to 100 where -100=extremely bearish, 0=neutral, 100=extremely bullish>, "reasons": ["<reason1>", "<reason2>"]}}"""


def _get_chunks(text: str) -> list[str]:
    """Split text into chunks of ~_CHUNK_WORD_SIZE words."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), _CHUNK_WORD_SIZE):
        chunks.append(" ".join(words[i:i + _CHUNK_WORD_SIZE]))
    return chunks


def _build_consolidation_prompt(
    segment: str,
    form_type: str,
    company: str,
    ticker: str | None,
    parsed_data: dict,
    chunk_summaries: list[str],
) -> str:
    template = _load_prompt(segment)
    combined = "\n\n".join(
        f"[Excerpt {i + 1} summary]: {s}" for i, s in enumerate(chunk_summaries)
    )
    return template.format(
        company=company,
        ticker=ticker or "N/A",
        form_type=form_type,
        parsed_data=json.dumps(parsed_data, indent=2, default=str),
        raw_text=combined[:6000],
    )


def _build_single_prompt(
    segment: str,
    form_type: str,
    company: str,
    ticker: str | None,
    parsed_data: dict,
    raw_text: str,
) -> str:
    template = _load_prompt(segment)
    return template.format(
        company=company,
        ticker=ticker or "N/A",
        form_type=form_type,
        parsed_data=json.dumps(parsed_data, indent=2, default=str),
        raw_text=raw_text[:6000],
    )


def _parse_response(text: str) -> dict:
    """Extract JSON from the SLM response, handling common formatting issues."""
    text = text.strip()

    # Direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding a JSON object with "summary" key anywhere in the text
    json_match = re.search(r"\{[^{}]*\"summary\"[^{}]*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback: use the raw text as the summary
    return {
        "summary": text[:300],
        "impact": 0,
        "reasons": ["Could not parse structured SLM response"],
    }


def _validate_impact(parsed: dict) -> dict:
    """Ensure impact is an integer clamped to [-100, 100]."""
    raw = parsed.get("impact", parsed.get("signal", 0))

    # Handle legacy string signal values just in case
    if isinstance(raw, str):
        mapping = {"bullish": 60, "bearish": -60, "neutral": 0}
        raw = mapping.get(raw.lower(), 0)

    try:
        score = int(raw)
    except (TypeError, ValueError):
        score = 0

    parsed["impact"] = max(-100, min(100, score))
    parsed.pop("signal", None)
    return parsed


async def _call_ollama(client: httpx.AsyncClient, prompt: str, num_predict: int = 500) -> str:
    """Send a single prompt to Ollama and return the response text."""
    settings = get_settings()
    response = await client.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": num_predict,
                "top_p": 0.9,
            },
        },
        timeout=settings.slm_timeout_seconds,
    )
    response.raise_for_status()
    return response.json().get("response", "")


async def summarise_filing(
    form_type: str,
    segment: str,
    company: str,
    ticker: str | None,
    parsed_data: dict,
    raw_text: str,
) -> dict:
    """Send filing to Ollama SLM and return structured result.

    For long filings (>_CHUNK_WORD_SIZE words), uses a two-phase approach:
    1. Summarize each chunk independently (like test.py)
    2. Consolidate chunk summaries into a final JSON response

    Returns dict with keys: summary, impact (int -100..100), reasons."""
    settings = get_settings()

    async with httpx.AsyncClient(timeout=settings.slm_timeout_seconds) as client:
        words = raw_text.split()

        if len(words) > _CHUNK_WORD_SIZE:
            # Phase 1: summarize each chunk
            chunks = _get_chunks(raw_text)
            chunk_summaries: list[str] = []
            for i, chunk in enumerate(chunks):
                log.info("  Chunk %d/%d for %s %s", i + 1, len(chunks), form_type, company)
                chunk_prompt = (
                    f"You are a financial analyst. Summarize this SEC filing excerpt "
                    f"from {company} ({form_type}) in 2-3 sentences focusing on key "
                    f"financial facts, risks, and signals:\n\n{chunk}"
                )
                summary_text = await _call_ollama(client, chunk_prompt, num_predict=200)
                chunk_summaries.append(summary_text.strip())

            # Phase 2: consolidate into final structured JSON
            final_prompt = _build_consolidation_prompt(
                segment, form_type, company, ticker, parsed_data, chunk_summaries
            )
            result_text = await _call_ollama(client, final_prompt, num_predict=500)
        else:
            # Short filing: single-pass prompt
            prompt = _build_single_prompt(
                segment, form_type, company, ticker, parsed_data, raw_text
            )
            result_text = await _call_ollama(client, prompt, num_predict=500)

    parsed = _parse_response(result_text)
    return _validate_impact(parsed)
