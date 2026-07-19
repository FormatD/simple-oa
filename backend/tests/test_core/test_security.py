"""Tests for core security module: password hashing, JWT, TOTP, password policy."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import (
    PasswordPolicyError,
    calculate_lockout_duration,
    check_login_lockout,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    hash_token,
    is_password_expired,
    validate_password_policy,
    verify_password,
    verify_totp_code,
)
from app.config import settings


# ─── Password hashing ───────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_password_returns_different_hash(self):
        pwd = "SecureP@ss1"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        assert h1 != h2
        assert h1.startswith("$2b$")

    def test_verify_password_correct(self):
        pwd = "SecureP@ss1"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("SecureP@ss1")
        assert verify_password("WrongP@ss1", hashed) is False

    def test_verify_password_empty(self):
        hashed = hash_password("SecureP@ss1")
        assert verify_password("", hashed) is False


# ─── Password policy ─────────────────────────────────────────────────

class TestPasswordPolicy:
    def test_valid_password_passes(self):
        validate_password_policy("StrongP@ss1")

    def test_too_short(self):
        with pytest.raises(PasswordPolicyError) as exc:
            validate_password_policy("Sh0!r")
        assert "at least" in str(exc.value)

    def test_missing_uppercase(self):
        with pytest.raises(PasswordPolicyError) as exc:
            validate_password_policy("lowercase1!")
        assert "uppercase" in str(exc.value)

    def test_missing_lowercase(self):
        with pytest.raises(PasswordPolicyError) as exc:
            validate_password_policy("UPPERCASE1!")
        assert "lowercase" in str(exc.value)

    def test_missing_digit(self):
        with pytest.raises(PasswordPolicyError) as exc:
            validate_password_policy("NoDigits!")
        assert "digit" in str(exc.value)

    def test_missing_special_char(self):
        with pytest.raises(PasswordPolicyError) as exc:
            validate_password_policy("NoSpecial1")
        assert "special" in str(exc.value)

    def test_boundary_length(self):
        validate_password_policy("Abcd123!")
        with pytest.raises(PasswordPolicyError):
            validate_password_policy("Abc123!")


# ─── Password expiry ─────────────────────────────────────────────────

class TestPasswordExpiry:
    def test_expired_when_none(self):
        assert is_password_expired(None) is True

    def test_not_expired_when_recent(self):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        assert is_password_expired(recent) is False

    def test_expired_when_old(self):
        old = datetime.now(timezone.utc) - timedelta(days=100)
        assert is_password_expired(old) is True

    def test_not_expired_barely_under_threshold(self):
        # 89 days should not be expired
        recent = datetime.now(timezone.utc) - timedelta(days=89)
        assert is_password_expired(recent) is False

    def test_expired_beyond_threshold(self):
        beyond = datetime.now(timezone.utc) - timedelta(days=90, hours=1)
        assert is_password_expired(beyond) is True


# ─── Login lockout ───────────────────────────────────────────────────

class TestLoginLockout:
    def test_not_locked_when_none(self):
        assert check_login_lockout(0, None) is False

    def test_locked_when_future(self):
        future = datetime.now(timezone.utc) + timedelta(minutes=15)
        assert check_login_lockout(5, future) is True

    def test_unlocked_when_past(self):
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert check_login_lockout(5, past) is False

    def test_calculate_lockout_duration_increases(self):
        d1 = calculate_lockout_duration(6)
        d2 = calculate_lockout_duration(7)
        assert d1 == timedelta(minutes=30)
        assert d2 == timedelta(minutes=60)

    def test_calculate_lockout_at_threshold(self):
        d = calculate_lockout_duration(5)
        assert d == timedelta(minutes=15)


# ─── JWT Tokens ──────────────────────────────────────────────────────

class TestJWTTokens:
    def test_create_access_token_returns_string(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_valid_access_token(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_decode_access_token_with_extra_claims(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, {"totp_required": "true"})
        payload = decode_access_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["totp_required"] == "true"

    def test_reject_expired_access_token(self):
        pytest.importorskip("freezegun")
        from freezegun import freeze_time
        user_id = uuid.uuid4()
        with freeze_time("2020-01-01"):
            token = create_access_token(user_id)
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token(token)

    def test_create_and_decode_refresh_token(self):
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id)
        payload = decode_refresh_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_reject_wrong_secret_token_type(self):
        """An access token (signed with JWT_SECRET_KEY) cannot be decoded
        as a refresh token (signed with JWT_REFRESH_SECRET_KEY)."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        with pytest.raises(ValueError, match="Invalid token"):
            decode_refresh_token(token)

    def test_reject_wrong_token_type_claim(self):
        """A token signed with the refresh key but with 'access' type should
        be rejected with 'Invalid token type'."""
        from jose import jwt
        from datetime import datetime, timezone, timedelta
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        claims = {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(days=30),
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(claims, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(ValueError, match="Invalid token type"):
            decode_refresh_token(token)

    def test_reject_tampered_token(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token(tampered)

    def test_hash_token(self):
        token = "some-random-token-value"
        h = hash_token(token)
        assert h == hash_token(token)
        assert len(h) == 64


# ─── TOTP MFA ────────────────────────────────────────────────────────

class TestTOTP:
    def test_generate_totp_secret(self):
        secret = generate_totp_secret()
        assert len(secret) > 10
        assert isinstance(secret, str)

    def test_get_totp_uri(self):
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@example.com")
        assert "otpauth://" in uri
        assert "user%40example.com" in uri

    def test_verify_totp_code(self):
        import pyotp
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp_code(secret, code) is True

    def test_verify_totp_code_wrong(self):
        secret = generate_totp_secret()
        assert verify_totp_code(secret, "000000") is False

    def test_totp_secret_is_random(self):
        s1 = generate_totp_secret()
        s2 = generate_totp_secret()
        assert s1 != s2
