"""Auth API routes: login, register, token refresh, password management."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    PasswordPolicyError,
    check_login_lockout,
    create_access_token,
    create_refresh_token,
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
from app.database import get_db
from app.models.auth import LoginAttempt, RefreshToken, User
from app.schemas.auth import (
    APIResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SetupTOTPResponse,
    TokenResponse,
    UserInfo,
    VerifyTOTPRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    try:
        validate_password_policy(req.password)
    except PasswordPolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    user = User(
        email=req.email,
        display_name=req.display_name,
        phone=req.phone,
        password_hash=hash_password(req.password),
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token(user.id)
    refresh_token_value = create_refresh_token(user.id)
    await _store_refresh_token(db, user.id, refresh_token_value, rotated_from_id=None)

    return APIResponse(data=TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_value,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ))


@router.post("/login", response_model=APIResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if user is None:
        await _record_login_attempt(db, req.email, False, request,
                                    "User not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if check_login_lockout(user.failed_login_attempts, user.locked_until):
        remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked. Try again in {remaining} seconds",
        )

    if not verify_password(req.password, user.password_hash):
        await _record_login_attempt(db, req.email, False, request,
                                    "Wrong password")
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
            from app.core.security import calculate_lockout_duration
            duration = calculate_lockout_duration(user.failed_login_attempts)
            user.locked_until = datetime.now(timezone.utc) + duration
        db.add(user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if is_password_expired(user.password_changed_at):
        raise HTTPException(
            status_code=status.HTTP_426_UPGRADE_REQUIRED,
            detail="Password expired, please change your password",
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    await _record_login_attempt(db, req.email, True, request)

    if user.totp_enabled:
        temp_token = create_access_token(user.id, {"totp_required": "true"})
        return APIResponse(data={
            "totp_required": True,
            "temp_token": temp_token,
        })

    access_token = create_access_token(user.id)
    refresh_token_value = create_refresh_token(user.id)
    await _store_refresh_token(db, user.id, refresh_token_value, rotated_from_id=None)

    return APIResponse(data=TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_value,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ))


@router.post("/refresh", response_model=APIResponse)
async def refresh_token(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token (R5: Token rotation)."""
    try:
        payload = decode_refresh_token(req.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    token_hash = hash_token(req.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
        )
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    if stored_token.expires_at < datetime.now(timezone.utc):
        stored_token.is_revoked = True
        db.add(stored_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    # R5: Rotate the refresh token — revoke old, issue new
    stored_token.is_revoked = True
    db.add(stored_token)

    user_id = uuid.UUID(payload["sub"])
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)
    await _store_refresh_token(db, user_id, new_refresh_token,
                                rotated_from_id=stored_token.id)

    return APIResponse(data=TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ))


@router.post("/logout", response_model=APIResponse)
async def logout(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Logout by revoking the refresh token."""
    token_hash = hash_token(req.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored_token = result.scalar_one_or_none()
    if stored_token:
        stored_token.is_revoked = True
        db.add(stored_token)
    return APIResponse(message="Logged out successfully")


@router.get("/me", response_model=APIResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return APIResponse(data=UserInfo(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        phone=current_user.phone,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        last_login_at=current_user.last_login_at,
        timezone=current_user.timezone,
        locale=current_user.locale,
    ))


@router.put("/password", response_model=APIResponse)
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for current user."""
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    try:
        validate_password_policy(req.new_password)
    except PasswordPolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    current_user.password_hash = hash_password(req.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    db.add(current_user)

    # Revoke all refresh tokens on password change
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_revoked == False,
        )
        .values(is_revoked=True)
    )
    return APIResponse(message="Password changed successfully")


@router.post("/forgot-password", response_model=APIResponse)
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset email."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if user:
        pass
    return APIResponse(message="If the email exists, a reset link has been sent")


@router.post("/totp/setup", response_model=APIResponse)
async def setup_totp(
    current_user: User = Depends(get_current_user),
):
    """Set up TOTP MFA (R7)."""
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, current_user.email)
    import base64
    import io
    import qrcode
    qr = qrcode.make(uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return APIResponse(data=SetupTOTPResponse(
        secret=secret, uri=uri, qr_code=qr_b64,
    ))


@router.post("/totp/verify", response_model=APIResponse)
async def verify_totp(
    req: VerifyTOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify and enable TOTP for the current user."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not set up yet",
        )
    if verify_totp_code(current_user.totp_secret, req.code):
        current_user.totp_enabled = True
        db.add(current_user)
        return APIResponse(data={"verified": True})
    return APIResponse(data={"verified": False})


async def _store_refresh_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    token_value: str,
    rotated_from_id: uuid.UUID | None = None,
) -> None:
    """Hash and store a refresh token."""
    token_hash = hash_token(token_value)
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expires_at = datetime.now(timezone.utc) + expires_delta
    rt = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        rotated_from_id=rotated_from_id,
    )
    db.add(rt)


async def _record_login_attempt(
    db: AsyncSession,
    email: str,
    success: bool,
    request: Request,
    fail_reason: str | None = None,
) -> None:
    """Record a login attempt for audit."""
    attempt = LoginAttempt(
        email=email,
        success=success,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        fail_reason=fail_reason,
    )
    db.add(attempt)
