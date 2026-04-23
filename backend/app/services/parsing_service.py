"""Contract parsing and metadata extraction utilities."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from io import BytesIO

import fitz

from app.services.redaction_service import RedactionService

CLAUSE_PATTERNS: dict[str, list[str]] = {
    "security": ["security", "data protection", "confidentiality", "encryption"],
    "royalty/payment": ["payment", "fee", "royalty", "invoice"],
    "liability": ["liability", "indemn", "damages", "limitation of liability"],
    "termination": ["termination", "terminate", "breach", "cure period"],
    "governing law": ["governing law", "jurisdiction", "venue", "laws of"],
}

STRONG_TERMS: dict[str, list[str]] = {
    "security": ["must", "shall", "iso 27001", "soc 2", "within 24 hours"],
    "royalty/payment": ["net 30", "fixed fee", "audit right"],
    "liability": ["cap", "indemnify", "unlimited"],
    "termination": ["for cause", "for convenience", "30 days"],
    "governing law": ["exclusive jurisdiction", "state of", "federal courts"],
}

RISK_MAP = {"security": "Critical", "liability": "High", "termination": "High", "royalty/payment": "Medium", "governing law": "Low"}


class ParsingService:
    """Extracts text, metadata, and clause-level findings from contracts."""

    def __init__(self, redaction_service: RedactionService) -> None:
        self._redaction_service = redaction_service

    def extract_text(self, filename: str, content: bytes) -> str:
        """Extract plain text from PDF or text input bytes."""

        lower_name = filename.lower()
        if lower_name.endswith(".pdf"):
            with fitz.open(stream=BytesIO(content), filetype="pdf") as document:
                return "\n".join(page.get_text("text") for page in document)
        return content.decode("utf-8", errors="ignore")

    @staticmethod
    def extract_metadata(text: str) -> dict[str, str | bool | None]:
        """Infer contract metadata from text without manual input."""

        vendor_match = re.search(r"between\s+([^\n,]+?)\s+and", text, flags=re.IGNORECASE)
        vendor = vendor_match.group(1).strip() if vendor_match else "Unknown Vendor"

        effective = _extract_date_after_label(text, "effective date")
        expiry = _extract_date_after_label(text, "(?:expiry|expiration|end) date")

        normalized = text.lower()
        category = "General"
        if "non-disclosure" in normalized or "nda" in normalized:
            category = "NDA"
        elif "master services" in normalized or "msa" in normalized:
            category = "MSA"
        elif "software as a service" in normalized or "saas" in normalized:
            category = "SaaS"

        auto_renewal = bool(re.search(r"auto[-\s]?renew|automatic renewal", normalized))
        return {
            "vendor": vendor,
            "effectiveDate": effective,
            "expiryDate": expiry,
            "category": category,
            "autoRenewal": auto_renewal,
        }

    @staticmethod
    def chunk_text(text: str) -> list[str]:
        """Split contract text into clause-like chunks."""

        pieces = [p.strip() for p in re.split(r"\n{2,}|(?<=\.)\s+(?=[A-Z])", text) if p.strip()]
        return [piece[:1200] for piece in pieces]

    def analyze_clauses(self, text: str) -> list[dict[str, str | bool]]:
        """Analyze required clauses and return findings with redacted excerpts."""

        lowered = text.lower()
        chunks = self.chunk_text(text)
        results: list[dict[str, str | bool]] = []

        for clause_name, keywords in CLAUSE_PATTERNS.items():
            matched = next((chunk for chunk in chunks if any(word in chunk.lower() for word in keywords)), None)
            found = matched is not None
            quality = "absent"
            excerpt = ""
            if matched:
                excerpt = self._redaction_service.redact(matched[:400])
                quality = "strong" if any(term in matched.lower() for term in STRONG_TERMS[clause_name]) else "weak"

            if quality == "absent":
                gap = f"Missing {clause_name} clause"
            elif quality == "weak":
                gap = f"{clause_name} clause is vendor-favorable or incomplete"
            else:
                gap = f"{clause_name} clause aligns with baseline"

            results.append(
                {
                    "name": clause_name,
                    "found": found,
                    "quality": quality,
                    "redactedExcerpt": excerpt,
                    "gapDescription": gap,
                    "riskLevel": RISK_MAP[clause_name],
                }
            )

        return results


def _extract_date_after_label(text: str, label_pattern: str) -> str | None:
    match = re.search(
        rf"{label_pattern}\s*[:\-]?\s*((?:\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})|(?:\d{{4}}-\d{{2}}-\d{{2}})|(?:[A-Za-z]+\s+\d{{1,2}},\s+\d{{4}}))",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    candidate = match.group(1)
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(candidate, fmt).replace(tzinfo=UTC)
            return parsed.date().isoformat()
        except ValueError:
            continue
    return candidate
