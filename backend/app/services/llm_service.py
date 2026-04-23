"""Single AI gateway for all model interactions."""

from __future__ import annotations

import os

from app.services.redaction_service import RedactionService


class LLMService:
    """AI abstraction layer; only accepts redacted excerpts."""

    def __init__(self, redaction_service: RedactionService) -> None:
        self._redaction_service = redaction_service

    def summarize_gap(self, redacted_excerpt: str, clause_name: str) -> str:
        """Return recommendation description using safe redacted text only."""

        sanitized = self._redaction_service.redact(redacted_excerpt)
        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            return f"Review and strengthen {clause_name} clause using approved baseline wording."
        return f"Review and strengthen {clause_name} clause using approved baseline wording."  # Placeholder for private endpoint integration
