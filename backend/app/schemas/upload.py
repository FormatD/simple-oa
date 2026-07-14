"""File upload schemas."""
from __future__ import annotations

from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    filename: str
    original_filename: str
    mime_type: str
    size: int
    url: str
    created_at: str
    updated_at: str
