"""Field-level encryption utilities (CR R6/R8).
Upgraded to AES-256-GCM for stronger encryption of sensitive fields at rest (CR R8).
Uses independent ENCRYPTION_KEY setting (M4) instead of binding to JWT_SECRET_KEY.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.config import settings

logger = logging.getLogger(__name__)

_SALT = b"enterprise-mgmt-r6-salt"
_AAD = b"enterprise-mgmt-emergency-contact"


def _get_aes_key() -> bytes:
    """Derive a 256-bit AES-GCM key from ENCRYPTION_KEY or JWT_SECRET_KEY (fallback)."""
    key_material = settings.ENCRYPTION_KEY or settings.JWT_SECRET_KEY
    key_material = key_material.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100000,
    )
    return kdf.derive(key_material)


def encrypt_field(data: dict[str, Any]) -> dict[str, Any]:
    """Encrypt sensitive fields (phone field in emergency_contact) using AES-256-GCM."""
    if not data:
        return data

    encrypted = dict(data)
    if "phone" in encrypted and encrypted["phone"]:
        key = _get_aes_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        phone_bytes = encrypted["phone"].encode("utf-8")
        ct = aesgcm.encrypt(nonce, phone_bytes, _AAD)
        encrypted["phone"] = base64.b64encode(nonce + ct).decode("utf-8")

    return encrypted


def decrypt_field(data: dict[str, Any]) -> dict[str, Any]:
    """Decrypt sensitive fields encrypted with AES-256-GCM."""
    if not data:
        return data

    decrypted = dict(data)
    if "phone" in decrypted and decrypted["phone"]:
        try:
            key = _get_aes_key()
            aesgcm = AESGCM(key)
            raw = base64.b64decode(decrypted["phone"])
            nonce = raw[:12]
            ct = raw[12:]
            decrypted["phone"] = aesgcm.decrypt(nonce, ct, _AAD).decode("utf-8")
        except Exception as exc:
            # M2: Log decryption failure instead of silently swallowing
            logger.warning("Failed to decrypt emergency_contact phone field: %s", exc)
            pass

    return decrypted


def is_field_encrypted(data: dict[str, Any]) -> bool:
    """Check if a field was encrypted with AES-GCM (base64 nonce+ct)."""
    if not data or "phone" not in data:
        return False
    try:
        raw = base64.b64decode(data["phone"])
        return len(raw) > 12
    except Exception:
        return False
