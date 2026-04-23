"""FastAPI app for AI contract compliance dashboard backend."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    Contract,
    ContractListItem,
    StandardsUploadResponse,
    TokenResponse,
    UploadResponse,
    UserTokenRequest,
)
from app.security import create_access_token, get_current_user
from app.services.encryption_service import EncryptionService
from app.services.llm_service import LLMService
from app.services.parsing_service import ParsingService
from app.services.redaction_service import RedactionService
from app.services.repository import Repository
from app.services.scoring_service import ScoringService
from app.services.vector_store import EncryptedVectorStore

app = FastAPI(title="Contract Compliance Dashboard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redaction_service = RedactionService()
encryption_service = EncryptionService()
repository = Repository(encryption_service=encryption_service)
parsing_service = ParsingService(redaction_service=redaction_service)
scoring_service = ScoringService()
llm_service = LLMService(redaction_service=redaction_service)
vector_store = EncryptedVectorStore(encryption_service=encryption_service)


@app.post("/api/auth/token", response_model=TokenResponse)
def issue_token(payload: UserTokenRequest) -> TokenResponse:
    """Issue a JWT access token for a provided user ID."""

    return TokenResponse(access_token=create_access_token(payload.userId))


@app.post("/api/contracts/upload", response_model=UploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    vendor: str | None = Form(default=None),
    effectiveDate: str | None = Form(default=None),
    category: str | None = Form(default=None),
    current_user: str = Depends(get_current_user),
) -> UploadResponse:
    """Upload, parse, analyze, and store a contract with encrypted text at rest."""

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload")

    contract_id = str(uuid4())
    extracted_text = parsing_service.extract_text(file.filename or "uploaded", content)
    metadata = parsing_service.extract_metadata(extracted_text)

    contract = Contract(
        id=contract_id,
        fileName=file.filename or "uploaded",
        vendor=vendor or str(metadata["vendor"]),
        effectiveDate=effectiveDate or _to_str(metadata["effectiveDate"]),
        expiryDate=_to_str(metadata["expiryDate"]),
        category=category or str(metadata["category"]),
        autoRenewal=bool(metadata["autoRenewal"]),
        uploadedAt=datetime.now(tz=UTC),
    )
    repository.save_contract(contract=contract, raw_text=extracted_text, owner_id=current_user)

    chunks = parsing_service.chunk_text(extracted_text)
    vector_store.add_chunks(contract_id=contract_id, chunks=chunks)

    clause_findings = parsing_service.analyze_clauses(extracted_text)
    _apply_baseline_comparison(clause_findings)
    for finding in clause_findings:
        if finding["quality"] != "strong":
            finding["gapDescription"] = llm_service.summarize_gap(
                str(finding["redactedExcerpt"]), str(finding["name"])
            )
            repository.add_audit_log(current_user, contract_id, "ai_call")

    analysis = scoring_service.score_contract(
        contract_id=contract_id,
        clauses=clause_findings,
        auto_renewal=contract.autoRenewal,
        effective_date=contract.effectiveDate,
        expiry_date=contract.expiryDate,
    )
    repository.analyses[contract_id] = analysis
    repository.add_audit_log(current_user, contract_id, "upload_contract")

    return UploadResponse(contractId=contract_id)


@app.get("/api/contracts", response_model=list[ContractListItem])
def list_contracts(
    status_filter: str | None = None,
    vendor: str | None = None,
    riskLevel: str | None = None,
    current_user: str = Depends(get_current_user),
) -> list[ContractListItem]:
    """Return contract list filtered by status, vendor, and risk level."""

    rows: list[ContractListItem] = []
    for contract_id, contract in repository.contracts.items():
        if repository.owner_by_contract.get(contract_id) != current_user:
            continue
        analysis = repository.analyses.get(contract_id)
        if not analysis:
            continue

        max_risk = _max_risk(analysis)
        if status_filter and analysis.status.lower() != status_filter.lower():
            continue
        if vendor and vendor.lower() not in contract.vendor.lower():
            continue
        if riskLevel and riskLevel.lower() != max_risk.lower():
            continue

        repository.add_audit_log(current_user, contract_id, "list_contract")
        rows.append(
            ContractListItem(
                contract=contract,
                score=analysis.score,
                status=analysis.status,
                maxRiskLevel=max_risk,
                alerts=analysis.alerts,
            )
        )
    return rows


@app.get("/api/contracts/{contract_id}/analysis")
def get_analysis(contract_id: str, current_user: str = Depends(get_current_user)):
    """Return clause-level analysis and recommendations for one contract."""

    _check_access(contract_id, current_user)
    analysis = repository.analyses.get(contract_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    repository.add_audit_log(current_user, contract_id, "view_analysis")
    return analysis.model_dump()


@app.get("/api/contracts/{contract_id}/report")
def export_report(contract_id: str, current_user: str = Depends(get_current_user)):
    """Export compliance report as JSON payload."""

    _check_access(contract_id, current_user)
    contract = repository.contracts.get(contract_id)
    analysis = repository.analyses.get(contract_id)
    if contract is None or analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    repository.add_audit_log(current_user, contract_id, "export_report")
    return {
        "contract": contract.model_dump(),
        "analysis": analysis.model_dump(),
        "generatedAt": datetime.now(tz=UTC).isoformat(),
    }


@app.post("/api/standards/upload", response_model=StandardsUploadResponse)
async def upload_standards(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
) -> StandardsUploadResponse:
    """Update in-memory baseline clause standards from a JSON document."""

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty standards file")

    try:
        parsed = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected JSON object")

    repository.standards = {str(k): str(v) for k, v in parsed.items()}
    repository.add_audit_log(current_user, "standards", "upload_standards")
    return StandardsUploadResponse(clauseCount=len(repository.standards))


def _check_access(contract_id: str, current_user: str) -> None:
    owner = repository.owner_by_contract.get(contract_id)
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    if owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _max_risk(analysis) -> str:
    ranking = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    risk = "Low"
    for clause in analysis.clauses:
        if ranking[clause.riskLevel] > ranking[risk]:
            risk = clause.riskLevel
    return risk


def _to_str(value: str | bool | None) -> str | None:
    return str(value) if isinstance(value, str) else None


def _apply_baseline_comparison(clause_findings: list[dict[str, str | bool]]) -> None:
    for finding in clause_findings:
        clause_name = str(finding["name"])
        baseline = repository.standards.get(clause_name)
        if not baseline:
            continue
        excerpt = str(finding["redactedExcerpt"])
        similarity = _token_similarity(excerpt, baseline)
        if similarity < 0.2 and str(finding["quality"]) == "strong":
            finding["quality"] = "weak"
            finding["gapDescription"] = f"{clause_name} appears outdated versus baseline"
        if str(finding["quality"]) == "absent":
            finding["gapDescription"] = f"Missing {clause_name} compared with baseline"


def _token_similarity(left: str, right: str) -> float:
    left_tokens = {token for token in left.lower().split() if token}
    right_tokens = {token for token in right.lower().split() if token}
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    universe = len(left_tokens | right_tokens)
    return overlap / universe
