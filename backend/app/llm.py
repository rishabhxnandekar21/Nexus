"""LLM layer: natural-language questions and written case briefs. F10.

Two hard rules, both from CLAUDE.md Section 6.

**The LLM never writes SQL and never touches the database.** It is given a
description of the schema and asked for structured filters only. Our code
validates those filters against a fixed allow-list and runs the query itself.
A model that returned `DROP TABLE` would simply fail validation.

**Everything degrades.** Campus Wi-Fi, an exhausted free tier and a missing API
key all land in the same place: a committed cache of the scripted demo
responses, and behind that a deterministic answer composed from the real data.
There is no path that produces a blank screen, and none that needs the network.

Reading order for the fallback chain:
    live model  ->  committed cache  ->  deterministic local answer
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import settings

CACHE_PATH = Path(__file__).resolve().parent / "demo_cache.json"

ENTITY_TYPES = ("person", "vehicle", "location", "phone", "organization", "crime_event")
REL_TYPES = ("co_accused", "called", "owns", "registered_at", "present_at",
             "family_of", "transacted_with", "suspect_in", "witness_in")
AGENCY_CODES = ("GJ_POLICE", "TELECOM", "RTO")

FILTER_KEYS = ("entity_types", "rel_types", "name_contains", "date_from",
               "date_to", "agency_codes")

SCHEMA_PROMPT = f"""You translate an investigator's question into structured filters.

Return ONLY a JSON object, no prose and no code fence, with these keys:
  entity_types   list, any of {list(ENTITY_TYPES)}
  rel_types      list, any of {list(REL_TYPES)}
  name_contains  string or null, a partial name to match
  date_from      "YYYY-MM-DD" or null
  date_to        "YYYY-MM-DD" or null
  agency_codes   list, any of {list(AGENCY_CODES)}
  interpretation string, one sentence restating the question as you read it

Omit a filter by using null or an empty list. Do not invent values outside the
lists above. Do not write SQL. The data covers 2019 to 2025.
"""


def _normalise(question: str) -> str:
    """Cache key: lowercase, collapsed whitespace, no trailing punctuation."""
    return re.sub(r"\s+", " ", question.strip().lower()).rstrip("?.!")


def load_cache() -> dict[str, Any]:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # A missing or corrupt cache must not take the endpoint down; the
        # deterministic path below still answers.
        return {"queries": {}, "briefs": {}}


def clean_filters(raw: dict) -> dict:
    """Keep only recognised keys with recognised values.

    This is the boundary. Anything the model invents - an extra key, a table
    name, a made-up entity type - is dropped here rather than reaching a query.
    """
    out: dict[str, Any] = {}

    types = [t for t in (raw.get("entity_types") or []) if t in ENTITY_TYPES]
    if types:
        out["entity_types"] = types

    rels = [r for r in (raw.get("rel_types") or []) if r in REL_TYPES]
    if rels:
        out["rel_types"] = rels

    codes = [c for c in (raw.get("agency_codes") or []) if c in AGENCY_CODES]
    if codes:
        out["agency_codes"] = codes

    name = raw.get("name_contains")
    if isinstance(name, str) and name.strip():
        out["name_contains"] = name.strip()[:100]

    for key in ("date_from", "date_to"):
        value = raw.get(key)
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            out[key] = value

    return out


def available() -> bool:
    return bool(settings.llm_api_key)


def _call_gemini(prompt: str) -> str:
    """One call, no retries. A retry loop just makes a dead network slower."""
    import google.generativeai as genai

    genai.configure(api_key=settings.llm_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model.generate_content(prompt).text


def _parse_json(text: str) -> dict:
    """Models wrap JSON in fences however they feel. Take the first object."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in the model response")
    return json.loads(match.group(0))


def interpret(question: str) -> tuple[dict, str, bool]:
    """Question -> (filters, interpretation, from_cache).

    Raises nothing. A failure anywhere falls through to the cache, and a cache
    miss falls through to an empty filter set, which the caller turns into an
    honest "I could not narrow this down" answer rather than an error page.
    """
    cache = load_cache()
    key = _normalise(question)

    if available():
        try:
            raw = _parse_json(_call_gemini(SCHEMA_PROMPT + f"\nQuestion: {question}\n"))
            interpretation = str(raw.get("interpretation") or "").strip()
            return clean_filters(raw), interpretation or f"Interpreted: {question}", False
        except Exception:
            # Deliberately broad. Quota, timeout, DNS, a malformed response and a
            # revoked key are all the same event here: use the cache.
            pass

    cached = cache.get("queries", {}).get(key)
    if cached:
        return clean_filters(cached.get("filters", {})), cached.get("interpretation", ""), True

    return {}, (f"No model available and this question is not in the demo cache, "
                f"so it was read literally: {question}"), True


def cached_answer(question: str) -> str | None:
    return load_cache().get("queries", {}).get(_normalise(question), {}).get("answer")


def compose_answer(question: str, filters: dict, names: list[str], total: int) -> str:
    """Deterministic answer from the real result set.

    Used when there is no model, and appended to a cached answer either way, so
    the numbers on screen always come from the database rather than from a
    recording made some other day.
    """
    if total == 0:
        return ("Nothing in the records you can see matches that. "
                + (f"Filters applied: {json.dumps(filters)}." if filters
                   else "No filters could be derived from the question."))
    shown = ", ".join(names[:5])
    more = f", and {total - len(names[:5])} more" if total > len(names[:5]) else ""
    return f"{total} record{'s' if total != 1 else ''} match: {shown}{more}."


def write_brief(entity_name: str, facts: str) -> tuple[str, bool]:
    """A written case summary. Returns (brief, from_cache).

    `facts` is assembled from the graph by the caller, so the model is
    summarising real data rather than being asked to recall anything.
    """
    if available():
        try:
            prompt = (
                "Write a short factual case brief, 4 to 6 sentences, for an "
                "investigator. Use only the facts given. Do not speculate about "
                "guilt, do not predict future behaviour, and do not invent names, "
                "dates or numbers.\n\n"
                f"Subject: {entity_name}\n{facts}\n"
            )
            return _call_gemini(prompt).strip(), False
        except Exception:
            pass

    cached = load_cache().get("briefs", {}).get(entity_name)
    if cached:
        return cached, True

    # The facts block is already a readable summary of the real network, so the
    # offline path is a genuine brief rather than an apology.
    return facts, True
