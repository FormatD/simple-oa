"""Row-Level Security (RLS) multi-tenant isolation (CR E5).

This module provides tenant and data isolation by enforcing
organization-scoped access at the query level.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


def set_tenant_context(session: AsyncSession, organization_id: uuid.UUID) -> None:
    """Set the tenant context for the current session (PostgreSQL RLS).

    This sets a session-level variable that PostgreSQL RLS policies
    can reference to filter rows by organization_id.
    """
    if not settings.ENABLE_RLS:
        return

    session.execute(
        text(f"SET app.current_tenant = '{organization_id}'")
    )


async def enable_rls_for_table(db: AsyncSession, table_name: str) -> None:
    """Enable RLS on a specific table."""
    await db.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
    await db.execute(text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;"))


async def create_rls_policy(
    db: AsyncSession,
    table_name: str,
    policy_name: str,
    using_expression: str,
) -> None:
    """Create an RLS policy on a table.

    Args:
        db: Database session
        table_name: Name of the table
        policy_name: Name for the policy
        using_expression: SQL expression for the USING clause
    """
    sql = text(
        f"""
        CREATE POLICY {policy_name} ON {table_name}
        FOR ALL
        USING ({using_expression});
        """
    )
    await db.execute(sql)


async def setup_tenant_rls(db: AsyncSession) -> None:
    """Set up RLS for tenant isolation across all organization-scoped tables.

    This creates a function that reads the session-level tenant context
    and creates policies on each table to filter by organization_id.
    """
    if not settings.ENABLE_RLS:
        return

    # Create the tenant context function
    await db.execute(
        text("""
        CREATE OR REPLACE FUNCTION current_tenant_id()
        RETURNS UUID AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.current_tenant', true), '')::UUID;
        EXCEPTION
            WHEN OTHERS THEN RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """)
    )

    # Tables that have organization_id for tenant isolation
    tenant_tables = [
        "departments",
        "organization_members",
        "roles",
        "employees",
        "attendance_records",
        "leave_types",
        "leave_balances",
        "leave_requests",
        "recruitment_positions",
        "salary_structures",
        "tasks",
        "wiki_folders",
        "wiki_pages",
        "notifications",
        "audit_logs",
    ]

    for table in tenant_tables:
        await enable_rls_for_table(db, table)
        await create_rls_policy(
            db,
            table,
            f"tenant_isolation_{table}",
            "organization_id = current_tenant_id()",
        )


def scope_by_organization(
    query,
    organization_id: uuid.UUID,
    org_column: str = "organization_id",
):
    """Apply organization scoping to a query for RLS at the application level.

    This is a fallback application-level scoping for environments where
    PostgreSQL RLS is not available or as a defense-in-depth layer.
    """
    if not settings.ENABLE_RLS:
        return query
    return query.where(text(f"{org_column} = :org_id")).params(org_id=organization_id)


def scope_by_department_hierarchy(
    query,
    user_id: uuid.UUID,
    dept_column: str = "department_id",
) -> object:
    """Scope query by department hierarchy so users can see their own
    department and sub-department data.

    This is a placeholder — the full implementation requires resolving
    the user's department tree from the department_members table.
    """
    # TODO: Full implementation with recursive CTE for department tree
    return query
