"""Render ETL worker skeleton for structured assembly-record extraction.

This module is intentionally lightweight: it reads mock or production議事録 text,
asks Gemini to return a strict JSON object, and exposes a CLI/SDK-friendly API
that later stages can call before persisting data to Firestore.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import logging
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from reaction_store import ReactionStoreError, get_firestore_client

logger = logging.getLogger("gijiraku.etl")

try:
    from google import genai
except ImportError:  # pragma: no cover - handled at runtime in deployment.
    genai = None


DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ETL_COLLECTION = "assembly_record_extractions"
MAX_SOURCE_TEXT_LENGTH = 100_000


class EtlAuthorizationError(RuntimeError):
    """Raised when an ETL request does not provide the configured secret."""


class EtlConfigurationError(RuntimeError):
    """Raised when the ETL runtime is missing required server configuration."""


def authorize_etl_request(provided_api_key: Optional[str]) -> None:
    configured_api_key = os.getenv("ETL_API_KEY", "").strip()
    if not configured_api_key:
        raise EtlConfigurationError("ETL_API_KEY is not configured")
    if not provided_api_key or not hmac.compare_digest(
        provided_api_key, configured_api_key
    ):
        raise EtlAuthorizationError("Invalid ETL API key")


def build_gemini_extract_prompt() -> str:
    return """
You are a careful municipal meeting parser.
Extract structured data from the following council meeting transcript.
Return valid JSON only, with the exact shape below.

{
  "meeting_date": "YYYY-MM-DD",
  "speaker": "発言者名",
  "topic": "議題トピック",
  "summary": "発言要約",
  "policy_signals": ["再開発", "補助金", "子育て"],
  "source_text_excerpt": "対象発言の短い引用"
}

Rules:
- Do not explain your reasoning.
- If a field is uncertain, use an empty string or an empty list.
- Keep JSON valid and parseable by Python json.loads.
- Use Japanese if the source is Japanese.
- Extract one record per significant speaking turn.
""".strip()


def get_gemini_client():
    if genai is None:
        raise RuntimeError("google-genai is not installed. Add it to requirements.txt.")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


def _extract_json_fragment(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError("Gemini response was empty.")

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    # Fallback: find the first JSON object in the response.
    brace_start = cleaned.find("{")
    brace_end = cleaned.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        return cleaned[brace_start:brace_end + 1]

    raise ValueError(f"Gemini response could not be parsed as JSON: {raw_text[:200]}")


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        fragment = _extract_json_fragment(raw_text)
        return json.loads(fragment)


def normalize_extracted_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Extracted assembly record must be a JSON object.")

    def normalized_text(field: str, maximum: int) -> str:
        value = payload.get(field, "")
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string.")
        return value.strip()[:maximum]

    meeting_date = normalized_text("meeting_date", 10)
    try:
        date.fromisoformat(meeting_date)
    except ValueError as exc:
        raise ValueError("meeting_date must use YYYY-MM-DD format.") from exc

    policy_signals = payload.get("policy_signals", [])
    if not isinstance(policy_signals, list):
        raise ValueError("policy_signals must be an array.")
    normalized_signals = []
    for value in policy_signals[:20]:
        if not isinstance(value, str):
            continue
        signal = value.strip()[:100]
        if signal and signal not in normalized_signals:
            normalized_signals.append(signal)

    record = {
        "meeting_date": meeting_date,
        "speaker": normalized_text("speaker", 200),
        "topic": normalized_text("topic", 300),
        "summary": normalized_text("summary", 2_000),
        "policy_signals": normalized_signals,
        "source_text_excerpt": normalized_text("source_text_excerpt", 500),
    }
    for required_field in ("topic", "summary", "source_text_excerpt"):
        if not record[required_field]:
            raise ValueError(f"{required_field} is required.")
    return record


def extract_assembly_record(raw_text: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """Call Gemini and parse a single structured record from raw meeting text."""
    source_text = raw_text.strip()
    if not source_text:
        raise ValueError("raw_text is required.")
    if len(source_text) > MAX_SOURCE_TEXT_LENGTH:
        raise ValueError(
            f"raw_text must be {MAX_SOURCE_TEXT_LENGTH} characters or fewer."
        )
    client = get_gemini_client()
    model = model_name or DEFAULT_MODEL
    prompt = build_gemini_extract_prompt()

    response = client.models.generate_content(
        model=model,
        contents=[prompt, source_text],
    )

    text_payload = getattr(response, "text", None)
    if not text_payload:
        raise ValueError("Gemini returned no text payload.")

    return normalize_extracted_record(parse_json_response(text_payload))


def load_source_text(file_path: str | os.PathLike[str]) -> str:
    path = Path(file_path)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Input file was not found: {path}") from exc


def save_extracted_record(
    payload: Dict[str, Any], *, collection_name: str = ETL_COLLECTION
) -> Dict[str, Any]:
    """Persist a parsed assembly record to Firestore. Returns metadata for callers."""
    normalized = normalize_extracted_record(payload)
    client = get_firestore_client()
    identity = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    document_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    ref = client.collection(collection_name).document(document_id)
    record = {
        **normalized,
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "source": "gemini_etl_worker",
    }
    try:
        ref.set(record, merge=True)
    except Exception as exc:
        logger.exception("Failed to persist ETL extraction (document_id=%s)", document_id)
        raise ReactionStoreError("Failed to persist ETL extraction") from exc
    return {"ok": True, "collection": collection_name, "document_id": document_id, "record": record}


def run_etl_batch(
    input_path: str | os.PathLike[str],
    output_path: Optional[str | os.PathLike[str]] = None,
    *,
    persist_to_firestore: bool = False,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Read source text, call Gemini, and optionally save structured JSON to disk."""
    raw_text = load_source_text(input_path)
    structured_record = extract_assembly_record(raw_text, model_name=model_name)

    if persist_to_firestore:
        save_extracted_record(structured_record)

    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(structured_record, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("ETL output written to %s", output)

    return structured_record


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render ETL worker to extract structured records from council minutes.")
    parser.add_argument("--input", required=True, help="Path to the raw meeting text file.")
    parser.add_argument("--output", default=None, help="Optional path where JSON output should be written.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model name to use.")
    parser.add_argument(
        "--persist-to-firestore",
        action="store_true",
        help="Persist the reviewed extraction to the ETL staging collection.",
    )
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    args = _build_cli_parser().parse_args()
    result = run_etl_batch(
        args.input,
        args.output,
        persist_to_firestore=args.persist_to_firestore,
        model_name=args.model,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
