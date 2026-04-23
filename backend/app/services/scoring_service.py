"""Compliance scoring and recommendation generation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models import Analysis, ClauseResult, Recommendation

PENALTIES = {
    "absent": 20,
    "weak": 8,
    "strong": 0,
}


class ScoringService:
    """Computes compliance score, status, and alerts from clause findings."""

    def score_contract(
        self,
        contract_id: str,
        clauses: list[dict[str, str | bool]],
        auto_renewal: bool,
        effective_date: str | None,
        expiry_date: str | None,
    ) -> Analysis:
        """Build full analysis object from clause findings and contract dates."""

        score = 100
        clause_models: list[ClauseResult] = []
        recommendations: list[Recommendation] = []

        for clause in clauses:
            quality = str(clause["quality"])
            score -= PENALTIES[quality]
            clause_model = ClauseResult(**clause)
            clause_models.append(clause_model)
            if quality != "strong":
                recommendations.append(
                    Recommendation(
                        clauseName=clause_model.name,
                        priority=clause_model.riskLevel,
                        description=f"Strengthen {clause_model.name} language to align with baseline standards.",
                        suggestedText=_suggested_text(clause_model.name),
                    )
                )

        score = max(0, min(score, 100))
        if score >= 80:
            status = "Compliant"
        elif score >= 50:
            status = "Partial"
        else:
            status = "Non-compliant"

        alerts = self._alerts(auto_renewal, effective_date, expiry_date)
        return Analysis(
            contractId=contract_id,
            score=score,
            status=status,
            analyzedAt=datetime.now(tz=UTC),
            clauses=clause_models,
            recommendations=recommendations,
            alerts=alerts,
        )

    @staticmethod
    def _alerts(auto_renewal: bool, effective_date: str | None, expiry_date: str | None) -> list[str]:
        now = datetime.now(tz=UTC).date()
        alerts: list[str] = []

        if auto_renewal and expiry_date:
            try:
                expiry = datetime.fromisoformat(expiry_date).date()
                if (expiry - now).days <= 90:
                    alerts.append("Auto-renewal due within 90 days")
            except ValueError:
                pass

        if effective_date:
            try:
                effective = datetime.fromisoformat(effective_date).date()
                if (now - effective).days > 365 * 3:
                    alerts.append("Legacy agreement older than 3 years")
            except ValueError:
                pass
        return alerts


def _suggested_text(clause_name: str) -> str:
    mapping = {
        "security": "Vendor shall maintain SOC 2 Type II controls and notify Customer of security incidents within 24 hours.",
        "royalty/payment": "All fees are fixed and payable net 30 days, with Customer audit rights once per year.",
        "liability": "Vendor shall indemnify Customer for third-party claims with liability cap not less than 2x annual fees.",
        "termination": "Customer may terminate for cause immediately after uncured breach and for convenience with 30 days notice.",
        "governing law": "This Agreement is governed by Customer-approved governing law and exclusive jurisdiction in agreed courts.",
    }
    return mapping.get(clause_name, "Update clause language to match approved baseline.")
