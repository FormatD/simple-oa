"""Security utilities: password hashing, JWT, TOTP, password policy."""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _prehash(password: str) -> str:
    """Pre-hash with SHA-256 to work around bcrypt's 72-byte limit."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# ─── Password hashing ───────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(_prehash(password))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_prehash(plain_password), hashed_password)
# ─── Password policy (R7) ────────────────────────────────────────

class PasswordPolicyError(ValueError):
    """Raised when a password violates policy."""
    pass

def validate_password_policy(password: str) -> None:
    """Validate password against the configured policy (CR R7)."""
    errors: list[str] = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(
            f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
        )

    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(
        r"[!@#$%^&*(),.?\":{}|<>_\-+=~`\[\];'\\/]", password
    ):
        errors.append("Password must contain at least one special character")

    if errors:
        raise PasswordPolicyError("; ".join(errors))

def is_password_expired(password_changed_at: datetime | None) -> bool:
    """Check if the password has exceeded the max age (R7)."""
    if not password_changed_at:
        return True
    max_age = timedelta(days=settings.PASSWORD_MAX_AGE_DAYS)
    return datetime.now(timezone.utc) - password_changed_at > max_age

def check_login_lockout(failed_attempts: int, locked_until: datetime | None) -> bool:
    """Check if the account is currently locked out (R7)."""
    if locked_until is None:
        return False
    if datetime.now(timezone.utc) < locked_until:
        return True
    return False

def calculate_lockout_duration(attempts: int) -> timedelta:
    """Calculate lockout duration based on consecutive failed attempts."""
    base = timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)

    # Exponential backoff: 15min, 30min, 1h, 2h, 4h...
    return base * (2 ** (attempts - settings.LOGIN_MAX_ATTEMPTS))
# ─── JWT Tokens ─────────────────────────────────────────────────

def create_access_token(
    subject: str | uuid.UUID,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(subject: str | uuid.UUID) -> str:
    """Create a long-lived JWT refresh token."""
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(subject),
        "type": "refresh",
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        claims, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")

def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_REFRESH_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")

def hash_token(token: str) -> str:
    """Hash a token for storage (one-way)."""
    return hashlib.sha256(token.encode()).hexdigest()
# ─── TOTP MFA (R7) ──────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    import pyotp
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str) -> str:
    """Get TOTP provisioning URI for QR code."""
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.TOTP_ISSUER)

def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a TOTP code."""
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
