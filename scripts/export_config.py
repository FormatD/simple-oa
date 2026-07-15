#!/usr/bin/env python3
"""Configuration export tool for disaster recovery.

Exports key system configuration (permissions, roles, leave types,
benefit items) to JSON files for backup and restore purposes.
"""
import json
import os
import sys
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(BASE_DIR, "backups", "config")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def export_metadata():
    """Export configuration metadata."""
    return {
        "exported_at": datetime.utcnow().isoformat(),
        "version": "1.0",
        "app": "simple-oa",
        "description": "System configuration export for disaster recovery",
    }


def export_system_config():
    """Placeholder: export system-level configuration.

    In a real deployment, this would query the database for:
    - Organization settings
    - Role definitions and permission mappings
    - Leave types
    - Benefit items
    - Department structure

    For now, we export the schema structure for reference.
    """
    metadata = export_metadata()

    config = {
        "metadata": metadata,
        "system": {
            "note": "This is a configuration structure reference. "
                    "In production, query the actual database for values.",
            "exportable_entities": [
                "organizations",
                "roles",
                "role_permissions",
                "permissions",
                "leave_types",
                "benefit_items",
                "positions",
                "departments",
            ],
            "restore_order": [
                "organizations",
                "departments",
                "positions",
                "roles",
                "permissions",
                "role_permissions",
                "leave_types",
                "benefit_items",
            ],
        },
        "database_schema_version": "1.0",
    }

    return config


def main():
    ensure_dir(EXPORT_DIR)

    config = export_system_config()

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(EXPORT_DIR, f"system_config_{timestamp}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"Configuration exported to: {filename}")
    print(f"  - Export timestamp: {config['metadata']['exported_at']}")
    print(f"  - Total entities: {len(config['system']['exportable_entities'])}")

    # Keep only last 30 config exports
    all_exports = sorted([
        f for f in os.listdir(EXPORT_DIR)
        if f.startswith("system_config_") and f.endswith(".json")
    ])
    while len(all_exports) > 30:
        old_file = os.path.join(EXPORT_DIR, all_exports.pop(0))
        os.remove(old_file)
        print(f"  Removed old export: {old_file}")


if __name__ == "__main__":
    main()
