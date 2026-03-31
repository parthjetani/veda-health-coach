#!/usr/bin/env python3
"""
Seed script - loads health product data into Supabase.

Usage:
    python scripts/seed_health_items.py              # Load v2 data (default)
    python scripts/seed_health_items.py --file seed_data.json  # Load specific file
    python scripts/seed_health_items.py --update      # Update existing entries

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env file.
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabase import create_client

from app.config import get_settings


def main():
    parser = argparse.ArgumentParser(description="Seed health items into Supabase")
    parser.add_argument(
        "--file",
        default="seed_data_v2.json",
        help="JSON file to load (default: seed_data_v2.json)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing entries instead of skipping",
    )
    args = parser.parse_args()

    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    # Load seed data
    seed_file = Path(__file__).parent / args.file
    if not seed_file.exists():
        print(f"Error: {seed_file} not found")
        sys.exit(1)

    with open(seed_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Loading {len(items)} health items from {args.file}...")

    success = 0
    updated = 0
    skipped = 0
    errors = 0

    for item in items:
        try:
            # Check if item already exists (by name)
            existing = (
                supabase.table("health_items")
                .select("id")
                .eq("item_name", item["item_name"])
                .limit(1)
                .execute()
            )

            if existing.data and len(existing.data) > 0:
                if args.update:
                    item_id = existing.data[0]["id"]
                    supabase.table("health_items").update(item).eq("id", item_id).execute()
                    print(f"  UPD:  {item['item_name']}")
                    updated += 1
                else:
                    print(f"  SKIP: {item['item_name']} (exists, use --update to overwrite)")
                    skipped += 1
                continue

            # Insert
            supabase.table("health_items").insert(item).execute()
            print(f"  OK:   {item['item_name']}")
            success += 1

        except Exception as e:
            print(f"  ERR:  {item['item_name']} - {e}")
            errors += 1

    print(f"\nDone! {success} added, {updated} updated, {skipped} skipped, {errors} errors.")


if __name__ == "__main__":
    main()
