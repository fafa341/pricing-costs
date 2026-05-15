"""
add_bom_otros.py — Add bom_otros TEXT column to Supabase products table.
=========================================================================
Run ONCE before deploying the two-table BOM editor split.

Usage:
  python3 pipeline/add_bom_otros.py

The script attempts to add the column via psycopg2 (direct Postgres connection).
If DATABASE_URL is not set, it prints the SQL to run manually in Supabase SQL Editor.
"""

import os
import sys
from pathlib import Path

SQL = "ALTER TABLE products ADD COLUMN IF NOT EXISTS bom_otros TEXT;"

def main():
    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        # Try constructing from Supabase connection string pattern
        # Format: postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
        project_url = os.environ.get("SUPABASE_PROJECT_URL", "")
        if "supabase.co" in project_url:
            project_ref = project_url.replace("https://", "").split(".")[0]
            db_host = f"db.{project_ref}.supabase.co"
            db_url_template = f"postgresql://postgres:[YOUR_DB_PASSWORD]@{db_host}:5432/postgres"
        else:
            db_url_template = "postgresql://postgres:[YOUR_DB_PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"

        print("=" * 60)
        print("Migration: Add bom_otros column")
        print("=" * 60)
        print()
        print("DATABASE_URL not set. Run this SQL manually in Supabase:")
        print()
        print(f"  {SQL}")
        print()
        print("Steps:")
        print("  1. Go to https://supabase.com/dashboard")
        print("  2. Open your project → SQL Editor")
        print("  3. Paste and run the SQL above")
        print()
        print("Or set DATABASE_URL and re-run this script:")
        print(f"  DATABASE_URL='{db_url_template}' python3 pipeline/add_bom_otros.py")
        sys.exit(0)

    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed. Run: pip install psycopg2-binary")
        print()
        print("Or run this SQL in Supabase SQL Editor:")
        print(f"  {SQL}")
        sys.exit(1)

    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        print(f"Running: {SQL}")
        cur.execute(SQL)
        print("✅ Column bom_otros added (or already exists).")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Run this SQL manually in Supabase SQL Editor:")
        print(f"  {SQL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
