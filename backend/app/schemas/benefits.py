"""Benefits module schemas."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class BenefitItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    annual_budget: float | None = None


class BenefitItemUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    category: str | None = None
    is_active: bool | None = None
    annual_budget: float | None = None


class BenefitItemResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    category: str | None = None
    is_active: bool
    annual_budget: float | None = None
    created_at: str
    updated_at: str


class EmployeeBenefitCreate(BaseModel):
    benefit_item_id: str
    effective_date: date
    expiry_date: date | None = None
    amount: float | None = None
    details: dict | None = None


class EmployeeBenefitUpdate(BaseModel):
    effective_date: date | None = None
    expiry_date: date | None = None
    amount: float | None = None
    is_active: bool | None = None


class EmployeeBenefitResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: str | None = None
    benefit_item_id: str
    benefit_item_name: str | None = None
    effective_date: str
    expiry_date: str | None = None
    amount: float | None = None
    is_active: bool
    created_at: str


class BenefitClaimCreate(BaseModel):
    benefit_item_id: str
    claim_date: date
    amount: float = Field(..., gt=0)
    description: str | None = None
    receipt_url: str | None = None


class BenefitClaimResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: str | None = None
    benefit_item_id: str
    benefit_item_name: str | None = None
    claim_date: str
    amount: float
    description: str | None = None
    status: str
    approved_by: str | None = None
    approved_at: str | None = None
    receipt_url: str | None = None
    created_at: str
