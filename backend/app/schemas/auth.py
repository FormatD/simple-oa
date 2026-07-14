"""Auth request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int = 3600
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)


class UserInfo(BaseModel):
    id: str
    email: str
    display_name: str
    phone: str | None = None
    avatar_url: str | None = None
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None = None
    timezone: str = "UTC"
    locale: str = "zh-CN"


class SetupTOTPResponse(BaseModel):
    secret: str
    uri: str
    qr_code: str  # base64 encoded QR code


class VerifyTOTPRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class VerifyTOTPResponse(BaseModel):
    verified: bool
    backup_codes: list[str] | None = None


# ─── Generic API response wrappers ──────────────────────────────

class APIResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any = None


class PaginatedData(BaseModel):
    data: list[Any]
    pagination: dict[str, int]


class PaginatedResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: PaginatedData
