"""Tests for Row-Level Security module: tenant isolation."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.rls import (
    scope_by_organization,
    scope_by_department_hierarchy,
    set_tenant_context,
)


class TestSetTenantContext:
    @patch("app.core.rls.settings")
    def test_set_tenant_context_when_rls_enabled(self, mock_settings):
        mock_settings.ENABLE_RLS = True
        org_id = uuid.uuid4()
        session = AsyncMock(spec=["execute"])
        set_tenant_context(session, org_id)
        session.execute.assert_called_once()
        call_args = session.execute.call_args[0][0]
        assert str(org_id) in str(call_args)

    @patch("app.core.rls.settings")
    def test_set_tenant_context_skipped_when_rls_disabled(self, mock_settings):
        mock_settings.ENABLE_RLS = False
        session = AsyncMock()
        set_tenant_context(session, uuid.uuid4())
        session.execute.assert_not_called()


class TestScopeByOrganization:
    @patch("app.core.rls.settings")
    def test_scope_by_organization_applies_filter(self, mock_settings):
        mock_settings.ENABLE_RLS = True
        org_id = uuid.uuid4()
        mock_query = MagicMock()
        result = scope_by_organization(mock_query, org_id)
        # The result should not be the original query — scope_by_organization
        # chains .where().params() so it returns the final mock in the chain.
        mock_query.where.assert_called_once()

    @patch("app.core.rls.settings")
    def test_scope_by_organization_skipped_when_disabled(self, mock_settings):
        mock_settings.ENABLE_RLS = False
        org_id = uuid.uuid4()
        mock_query = MagicMock()
        result = scope_by_organization(mock_query, org_id)
        assert result is mock_query
        mock_query.where.assert_not_called()


class TestScopeByDepartmentHierarchy:
    def test_scope_by_department_hierarchy_returns_query(self):
        user_id = uuid.uuid4()
        mock_query = MagicMock()
        result = scope_by_department_hierarchy(mock_query, user_id)
        assert result is mock_query
