"""
Lightweight migration script to bring DB schema up to date.

Usage:
  python migrate.py

It will:
- Create 'publications' table if missing
- Add new optional columns to 'shorts' table if missing

Notes:
- Uses generic SQL where possible to support Postgres and SQLite.
- For production, prefer Alembic.
"""
from datetime import datetime
from sqlalchemy import text, inspect
from database import engine

INSPECTOR = inspect(engine)


def table_exists(name: str) -> bool:
    return name in INSPECTOR.get_table_names()


def column_exists(table: str, column: str) -> bool:
    try:
        cols = {c['name'] for c in INSPECTOR.get_columns(table)}
        return column in cols
    except Exception:
        return False


def create_publications_table():
    ddl = text(
        """
        CREATE TABLE IF NOT EXISTS publications (
            id VARCHAR PRIMARY KEY,
            short_id VARCHAR NOT NULL,
            platform VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'queued',
            error_message TEXT NULL,
            external_post_id VARCHAR NULL,
            external_url VARCHAR NULL,
            payload TEXT NULL,
            created_at TIMESTAMP NULL,
            updated_at TIMESTAMP NULL
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(ddl)


def create_account_tokens_table():
    ddl = text(
        """
        CREATE TABLE IF NOT EXISTS account_tokens (
            id VARCHAR PRIMARY KEY,
            platform VARCHAR NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT NULL,
            expires_at TIMESTAMP NULL,
            user_id VARCHAR NULL,
            created_at TIMESTAMP NULL,
            updated_at TIMESTAMP NULL
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(ddl)


def add_short_columns():
    additions = [
        ("platform_title", "VARCHAR"),
        ("platform_description", "TEXT"),
        ("hashtags", "TEXT"),
        ("cta", "TEXT"),
        ("captions_srt", "TEXT"),
        ("captions_alt", "TEXT"),
        ("language", "VARCHAR"),
        ("thumbnail_copy", "TEXT"),
        ("thumbnail_style", "TEXT"),
    ]
    for col, typ in additions:
        if not column_exists("shorts", col):
            ddl = text(f"ALTER TABLE shorts ADD COLUMN {col} {typ}")
            try:
                with engine.begin() as conn:
                    conn.execute(ddl)
            except Exception:
                # Ignore if column already exists or ALTER not supported
                pass


def add_project_columns():
    """Add transcript caching columns to projects table."""
    additions = [
        ("transcript", "TEXT"),
        ("transcript_fetched_at", "TIMESTAMP"),
        ("video_description", "TEXT"),
    ]
    for col, typ in additions:
        if not column_exists("projects", col):
            ddl = text(f"ALTER TABLE projects ADD COLUMN {col} {typ}")
            try:
                with engine.begin() as conn:
                    conn.execute(ddl)
                    print(f"Added column '{col}' to projects table")
            except Exception as e:
                # Ignore if column already exists or ALTER not supported
                print(f"Could not add column '{col}': {e}")
                pass


def main():
    if not table_exists("publications"):
        create_publications_table()
    else:
        # ensure columns exist (in case table exists without columns)
        pass

    if not table_exists("account_tokens"):
        create_account_tokens_table()

    add_short_columns()
    add_project_columns()

    print("Migration completed.")


if __name__ == "__main__":
    main()
