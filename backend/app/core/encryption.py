"""Field-level encryption utilities (CR R6).
Uses symmetric Fernet encryption for sensitive fields at rest.
"""
from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

from app.config import settings

# Derive encryption key from the JWT secret (should use a dedicated key in production)
_SALT = b"enterprise-mgmt-r6-salt"


def _get_fernet() -> Fernet:
    """Derive Fernet key from settings (or env var for production)."""
    # Use a dedicated encryption key or derive from JWT secret
    key_material = settings.JWT_SECRET_KEY.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_material))
    return Fernet(key)


def encrypt_field(data: dict[str, Any]) -> dict[str, Any]:
    """Encrypt sensitive fields (phone field in emergency_contact)."""
    if not data:
        return data

    encrypted = dict(data)
    if "phone" in encrypted and encrypted["phone"]:
        fernet = _get_fernet()
        phone_bytes = encrypted["phone"].encode("utf-8")
        encrypted["phone"] = fernet.encrypt(phone_bytes).decode("utf-8")

    return encrypted


def decrypt_field(data: dict[str, Any]) -> dict[str, Any]:
    """Decrypt sensitive fields."""
    if not data:
        return data

    decrypted = dict(data)
    if "phone" in decrypted and decrypted["phone"]:
        try:
            fernet = _get_fernet()
            phone_bytes = decrypted["phone"].encode("utf-8")
            decrypted["phone"] = fernet.decrypt(phone_bytes).decode("utf-8")
        except Exception:
            # If decryption fails, return as-is (field may not be encrypted yet)
            pass

    return decrypted
