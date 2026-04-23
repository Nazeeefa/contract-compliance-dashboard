"""Pydantic data models for contract compliance APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["Critical", "High", "Medium", "Low"]
QualityLevel = Literal["strong", "weak", "absent"]
ComplianceStatus = Literal["Compliant", "Partial", "Non-compliant"]


class Contract(BaseModel):
    """Stored contract metadata."""

    id: str
    fileName: str
    vendor: str
    effectiveDate: str | None = None
    expiryDate: str | None = None
    category: str
    autoRenewal: bool
    uploadedAt: datetime


class ClauseResult(BaseModel):
    """Result for a single required clause."""

    name: str
    found: bool
    quality: QualityLevel
    redactedExcerpt: str
    gapDescription: str
    riskLevel: RiskLevel


class Recommendation(BaseModel):
    """Actionable recommendation for an identified gap."""

    clauseName: str
    priority: RiskLevel
    description: str
    suggestedText: str


class Analysis(BaseModel):
    """Overall compliance analysis result for a contract."""

    contractId: str
    score: int = Field(ge=0, le=100)
    status: ComplianceStatus
    analyzedAt: datetime
    clauses: list[ClauseResult]
    recommendations: list[Recommendation]
    alerts: list[str]


class AuditLog(BaseModel):
    """Metadata-only audit trail event."""

    userId: str
    contractId: str
    action: str
    timestamp: datetime


class UploadResponse(BaseModel):
    """Upload endpoint response."""

    contractId: str


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str
    token_type: str = "bearer"


class UserTokenRequest(BaseModel):
    """Simple auth request payload for POC."""

    userId: str


class ContractListItem(BaseModel):
    """List row for dashboard table."""

    contract: Contract
    score: int = Field(ge=0, le=100)
    status: ComplianceStatus
    maxRiskLevel: RiskLevel
    alerts: list[str]


class StandardsUploadResponse(BaseModel):
    """Response after standards library update."""

    clauseCount: int
