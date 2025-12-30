#!/usr/bin/env python3
"""
Script to manually initialize the database and create tables.
Run this once before deploying or to verify database connection.

Usage:
    python scripts/init_db.py
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set DATABASE_URL if not already set (for local testing)
if not os.environ.get("DATABASE_URL"):
    # Remove channel_binding=require as psycopg2 doesn't support it
    os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_IZsCq9oND2ic@ep-red-pond-a4gdwfd3-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

from app.database import init_db, engine, Base, RequestLog

def main():
    print("Initializing database...")
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')[:50]}...")

    try:
        init_db()
        print("✓ Database connection successful")

        # Verify table exists
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"✓ Tables in database: {tables}")

        if "RequestLogs" in tables:
            print("✓ RequestLogs table exists")

            # Show columns
            columns = inspector.get_columns("RequestLogs")
            print(f"  Columns: {[col['name'] for col in columns]}")
        else:
            print("✗ RequestLogs table NOT found - something went wrong")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
