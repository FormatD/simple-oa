"""Field-level encryption utilities (CR R6/R8).
Upgraded to AES-256-GCM for stronger encryption of sensitive fields at rest (CR R8).
"""
from __future__ import annotations

import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.config import settings

# Derive encryption key from the JWT secret (should use a dedicated key in production)
_SALT = b"enterprise-mgmt-r6-salt"
_AAD = b"enterprise-mgmt-emergency-contact"


def _get_aes_key() -> bytes:
    """Derive a 256-bit AES-GCM key from settings."""
    key_material = settings.JWT_SECRET_KEY.encode("utf-8")
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
        # Store as base64(nonce + ciphertext)
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
        except Exception:
            # If decryption fails, field may not be encrypted yet; return as-is
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
