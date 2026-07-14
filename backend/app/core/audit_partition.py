"""Audit log partition strategy (CR R9).

Implements monthly partitioning for the audit_logs table to enable:
- Efficient time-range queries
- Easy archival of old data
- Faster maintenance operations (partition-wise)

SQL to create partitioned table structure:

CREATE TABLE audit_logs (
    id UUID NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    actor_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(200) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    resource_name VARCHAR(500),
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions (example for 2026)
CREATE TABLE audit_logs_2026_01
    PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE audit_logs_2026_02
    PARTITION OF audit_logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- ... and so on for each month

-- Partition indexes (applied to each partition)
CREATE INDEX idx_audit_logs_org ON audit_logs(organization_id, created_at);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id, created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- For efficient partition pruning, run monthly as cron:
-- SELECT create_monthly_partition(NOW());
"""
from __future__ import annotations

from datetime import datetime, timezone


def get_partition_name(year: int, month: int) -> str:
    """Get the partition table name for a given year/month."""
    return f"audit_logs_{year:04d}_{month:02d}"


def get_partition_range(year: int, month: int) -> tuple[str, str]:
    """Get the date range for a partition."""
    from_start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        to_start = f"{year + 1:04d}-01-01"
    else:
        to_start = f"{year:04d}-{month + 1:02d}-01"
    return from_start, to_start


def partition_sql(year: int, month: int) -> str:
    """Generate SQL to create a monthly partition if it doesn't exist."""
    name = get_partition_name(year, month)
    from_start, to_start = get_partition_range(year, month)
    return f"""
    CREATE TABLE IF NOT EXISTS {name}
    PARTITION OF audit_logs
    FOR VALUES FROM ('{from_start}') TO ('{to_start}');
    """


def ensure_recent_partitions_sql(months_ahead: int = 3) -> list[str]:
    """Generate SQL to ensure partitions exist for recent/future months."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    statements = []
    for offset in range(-1, months_ahead + 1):
        dt = now.replace(day=1)
        if offset < 0:
            # Past month
            month = dt.month - 1
            year = dt.year
            if month == 0:
                month = 12
                year -= 1
        else:
            month = dt.month + offset
            year = dt.year
            while month > 12:
                month -= 12
                year += 1
        statements.append(partition_sql(year, month))
    return statements
