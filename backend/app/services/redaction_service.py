"""Redaction gateway for sensitive contract content before AI usage."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


class RedactionService:
    """Redacts dates, currency amounts, and likely party names."""

    _date_pattern = re.compile(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[a-z]*\s+\d{1,2},\s+\d{4})\b",
        flags=re.IGNORECASE,
    )
    _money_pattern = re.compile(r"(?:\$|USD\s?)\d[\d,]*(?:\.\d{1,2})?", flags=re.IGNORECASE)
    _party_pattern = re.compile(
        r"\b([A-Z][A-Za-z0-9&,.\-]{2,}\s(?:Inc\.?|LLC|Ltd\.?|Corporation|Corp\.?|Company|Co\.?))\b"
    )

    def redact(self, text: str) -> str:
        """Return text with sensitive entities replaced by placeholders."""

        redacted = self._date_pattern.sub("[REDACTED_DATE]", text)
        redacted = self._money_pattern.sub("[REDACTED_FINANCIAL]", redacted)
        redacted = self._party_pattern.sub("[REDACTED_PARTY]", redacted)
        return self._redact_numeric_amounts(redacted)

    @staticmethod
    def _redact_numeric_amounts(text: str) -> str:
        """Redact large bare numeric values that are likely financial figures."""

        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            try:
                value = Decimal(token.replace(",", ""))
            except InvalidOperation:
                return token
            if value >= 1000:
                return "[REDACTED_FINANCIAL]"
            return token

        return re.sub(r"\b\d{4,}(?:\.\d+)?\b", repl, text)
