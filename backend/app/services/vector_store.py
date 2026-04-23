"""Encrypted in-memory vector store abstraction for clause retrieval."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from app.services.encryption_service import EncryptionService


class EncryptedVectorStore:
    """Stores lightweight deterministic embeddings encrypted at rest."""

    def __init__(self, encryption_service: EncryptionService) -> None:
        self._encryption_service = encryption_service
        self._store: dict[str, list[str]] = defaultdict(list)

    def add_chunks(self, contract_id: str, chunks: list[str]) -> None:
        """Embed and store chunk vectors for a contract."""

        vectors = [self._embed(chunk) for chunk in chunks]
        payload = json.dumps(vectors)
        self._store[contract_id] = [self._encryption_service.encrypt(payload)]

    def get_vectors(self, contract_id: str) -> list[list[float]]:
        """Return decrypted vectors for a contract."""

        encrypted_payloads = self._store.get(contract_id, [])
        if not encrypted_payloads:
            return []
        payload = self._encryption_service.decrypt(encrypted_payloads[0])
        raw = json.loads(payload)
        return [[float(v) for v in row] for row in raw]

    @staticmethod
    def _embed(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [byte / 255.0 for byte in digest[:16]]
