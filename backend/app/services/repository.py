"""In-memory repository for encrypted contract and analysis records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.models import Analysis, AuditLog, Contract
from app.services.encryption_service import EncryptionService


@dataclass
class Repository:
    """Stores encrypted contract text and metadata keyed by contract ID."""

    encryption_service: EncryptionService
    contracts: dict[str, Contract] = field(default_factory=dict)
    encrypted_contract_text: dict[str, str] = field(default_factory=dict)
    analyses: dict[str, Analysis] = field(default_factory=dict)
    owner_by_contract: dict[str, str] = field(default_factory=dict)
    audit_logs: list[AuditLog] = field(default_factory=list)
    standards: dict[str, str] = field(default_factory=dict)

    def save_contract(self, contract: Contract, raw_text: str, owner_id: str) -> None:
        """Persist contract metadata and encrypted raw text."""

        self.contracts[contract.id] = contract
        self.encrypted_contract_text[contract.id] = self.encryption_service.encrypt(raw_text)
        self.owner_by_contract[contract.id] = owner_id

    def get_contract_text(self, contract_id: str) -> str | None:
        """Return decrypted raw text for internal server-side processing."""

        encrypted = self.encrypted_contract_text.get(contract_id)
        if not encrypted:
            return None
        return self.encryption_service.decrypt(encrypted)

    def add_audit_log(self, user_id: str, contract_id: str, action: str) -> None:
        """Append metadata-only audit event."""

        self.audit_logs.append(
            AuditLog(
                userId=user_id,
                contractId=contract_id,
                action=action,
                timestamp=datetime.now(tz=UTC),
            )
        )
