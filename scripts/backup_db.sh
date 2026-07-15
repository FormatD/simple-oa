#!/bin/bash
# Database backup script
# Usage: ./scripts/backup_db.sh [output_dir]

set -euo pipefail

# Default backup directory
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/simple_oa_backup_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Load environment
if [ -f .env.example ]; then
    export $(grep -v '^#' .env.example | xargs)
fi

# Check for pg_dump
if ! command -v pg_dump &> /dev/null; then
    echo "Error: pg_dump not found. Please install PostgreSQL client tools."
    exit 1
fi

# Build connection string from DATABASE_URL
DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/simple_oa}"

echo "=== Database Backup ==="
echo "Timestamp:  $(date)"
echo "Backup file: ${BACKUP_FILE}"
echo ""

# Perform backup
pg_dump \
    --dbname="${DB_URL}" \
    --format=custom \
    --verbose \
    --file="${BACKUP_FILE}" 2>&1

echo ""
echo "=== Backup Complete ==="
echo "File: ${BACKUP_FILE}"
echo "Size: $(du -h "${BACKUP_FILE}" | cut -f1)"

# Keep only last 7 days of backups
find "${BACKUP_DIR}" -name "simple_oa_backup_*.sql" -mtime +7 -delete
echo "Cleaned up backups older than 7 days"
