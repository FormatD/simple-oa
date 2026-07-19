"""Tests for field-level encryption module: AES-GCM encrypt/decrypt."""
from __future__ import annotations

import pytest

from app.core.encryption import decrypt_field, encrypt_field, is_field_encrypted


class TestFieldEncryption:
    def test_encrypt_phone_field(self):
        data = {"phone": "13800138000"}
        result = encrypt_field(data)
        assert result["phone"] != "13800138000"
        assert len(result["phone"]) > 20

    def test_decrypt_phone_field(self):
        data = {"phone": "13800138000"}
        encrypted = encrypt_field(data)
        decrypted = decrypt_field(encrypted)
        assert decrypted["phone"] == "13800138000"

    def test_roundtrip_preserves_other_fields(self):
        data = {"phone": "13800138000", "name": "John Doe", "address": "123 Main St"}
        encrypted = encrypt_field(data)
        assert encrypted["name"] == "John Doe"
        assert encrypted["address"] == "123 Main St"
        decrypted = decrypt_field(encrypted)
        assert decrypted["phone"] == "13800138000"
        assert decrypted["name"] == "John Doe"

    def test_empty_data_returns_empty(self):
        assert encrypt_field({}) == {}
        assert decrypt_field({}) == {}

    def test_none_data_returns_none(self):
        assert encrypt_field(None) is None
        assert decrypt_field(None) is None

    def test_no_phone_field_passes_through(self):
        data = {"name": "John"}
        assert encrypt_field(data) == data
        assert decrypt_field(data) == data

    def test_null_phone_does_not_encrypt(self):
        data = {"phone": None}
        result = encrypt_field(data)
        assert result["phone"] is None

    def test_tampered_data_detection(self):
        data = {"phone": "13800138000"}
        encrypted = encrypt_field(data)
        # Tamper with the ciphertext
        tampered = encrypted.copy()
        tampered["phone"] = encrypted["phone"][:-5] + "AAAAA"
        result = decrypt_field(tampered)
        # Should return original tampered value (decryption fails silently)
        # but is_field_encrypted still detects it as encrypted format
        assert is_field_encrypted(tampered) is True

    def test_is_field_encrypted_detects_encrypted(self):
        data = {"phone": "13800138000"}
        encrypted = encrypt_field(data)
        assert is_field_encrypted(encrypted) is True

    def test_is_field_encrypted_false_for_plaintext(self):
        data = {"phone": "13800138000"}
        assert is_field_encrypted(data) is False

    def test_is_field_encrypted_false_for_empty(self):
        assert is_field_encrypted({}) is False
        assert is_field_encrypted(None) is False

    def test_is_field_encrypted_false_no_phone(self):
        assert is_field_encrypted({"name": "test"}) is False
