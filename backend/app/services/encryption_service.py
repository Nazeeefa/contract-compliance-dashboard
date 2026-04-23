"""AES-256 encryption service for contract text and embeddings at rest."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionService:
    """Provides authenticated AES-256-GCM encryption and decryption."""

    def __init__(self) -> None:
        encoded = os.getenv("ENCRYPTION_KEY")
        if encoded:
            key = base64.urlsafe_b64decode(encoded)
        else:
            key = hashlib.sha256(b"local-development-key").digest()
        if len(key) != 32:
            raise ValueError("ENCRYPTION_KEY must decode to 32 bytes")
        self._aes = AESGCM(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a UTF-8 string and return base64 encoded ciphertext payload."""

        nonce = os.urandom(12)
        data = plaintext.encode("utf-8")
        encrypted = self._aes.encrypt(nonce, data, associated_data=None)
        return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt a base64 encoded ciphertext payload."""

        payload = base64.urlsafe_b64decode(encrypted_text)
        nonce = payload[:12]
        ciphertext = payload[12:]
        plaintext = self._aes.decrypt(nonce, ciphertext, associated_data=None)
        return plaintext.decode("utf-8")
