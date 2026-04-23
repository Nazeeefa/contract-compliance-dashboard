"""Unit tests for compliance scoring behavior."""

from datetime import UTC, datetime, timedelta

from app.services.scoring_service import ScoringService


def test_score_status_and_alerts() -> None:
    service = ScoringService()
    clauses = [
        {
            "name": "security",
            "found": True,
            "quality": "strong",
            "redactedExcerpt": "",
            "gapDescription": "",
            "riskLevel": "Critical",
        },
        {
            "name": "liability",
            "found": True,
            "quality": "weak",
            "redactedExcerpt": "",
            "gapDescription": "",
            "riskLevel": "High",
        },
        {
            "name": "termination",
            "found": False,
            "quality": "absent",
            "redactedExcerpt": "",
            "gapDescription": "",
            "riskLevel": "High",
        },
    ]
    today = datetime.now(tz=UTC).date()
    analysis = service.score_contract(
        contract_id="c1",
        clauses=clauses,
        auto_renewal=True,
        effective_date=(today - timedelta(days=365 * 4)).isoformat(),
        expiry_date=(today + timedelta(days=30)).isoformat(),
    )

    assert analysis.score == 72
    assert analysis.status == "Partial"
    assert len(analysis.recommendations) == 2
    assert "Auto-renewal due within 90 days" in analysis.alerts
    assert "Legacy agreement older than 3 years" in analysis.alerts
