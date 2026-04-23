"""Unit tests for clause detection and redaction behavior."""

from app.services.parsing_service import ParsingService
from app.services.redaction_service import RedactionService


def test_clause_detection_and_redaction() -> None:
    text = (
        "This Agreement is between Acme Corp and Example LLC. Effective Date: January 5, 2021. "
        "Vendor shall maintain SOC 2 security controls and notify within 24 hours. "
        "Payment fee is $12,000 due net 30 days. Governing law is the State of California."
    )
    parser = ParsingService(redaction_service=RedactionService())

    clauses = parser.analyze_clauses(text)
    security = next(item for item in clauses if item["name"] == "security")
    payment = next(item for item in clauses if item["name"] == "royalty/payment")

    assert security["found"] is True
    assert security["quality"] == "strong"
    assert payment["redactedExcerpt"].find("[REDACTED_FINANCIAL]") >= 0
