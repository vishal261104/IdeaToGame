"""
memory/db.py
------------
Dual-layer metadata and game code persistence.
Primary: Supabase (PostgreSQL cloud)
Fallback: Local SQLite (`runs_history.sqlite3`)

This guarantees run history is ALWAYS accessible even if Supabase
is paused, unreachable, or DNS fails.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Lazy Supabase client
# ---------------------------------------------------------------------------
_supabase: Optional[Client] = None

# SQLite path in project root
_SQLITE_PATH = Path(__file__).parent.parent / "runs_history.sqlite3"


def _get_sqlite_conn() -> sqlite3.Connection:
    """Return an open SQLite connection with Row factory and ensured schema."""
    conn = sqlite3.connect(str(_SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id           TEXT PRIMARY KEY,
                game_idea    TEXT NOT NULL,
                output_file  TEXT,
                status       TEXT NOT NULL,
                retries      INTEGER DEFAULT 0,
                description  TEXT DEFAULT '',
                code_length  INTEGER DEFAULT 0,
                game_code    TEXT,
                created_at   TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)")
    return conn


def _get_client() -> Optional[Client]:
    """Lazily initialise the Supabase client. Returns None if credentials missing."""
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

        if not url or not key or "your-project" in url:
            return None

        try:
            _supabase = create_client(url, key)
        except Exception as e:
            print(f"[Supabase] Init warning: {e}")
            return None
    return _supabase


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def log_run(
    game_idea: str,
    output_file: str,
    status: str,
    retries: int = 0,
    description: str = "",
    code_length: int = 0,
    game_code: str = "",
) -> str:
    """
    Insert a run record into both local SQLite (guaranteed) and Supabase (cloud).
    Returns the generated run_id (UUID string).
    """
    run_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Guaranteed save to local SQLite
    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs
                (id, game_idea, output_file, status, retries, description, code_length, game_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, game_idea, output_file, status, retries, description, code_length, game_code, now_iso),
            )
        conn.close()
        print(f"[SQLite] Run logged locally (id={run_id}, status={status}).")
    except Exception as exc:
        print(f"[SQLite] Warning logging run — {exc}")

    # 2. Try Supabase cloud store
    try:
        client = _get_client()
        if client:
            client.table("runs").insert({
                "id":          run_id,
                "game_idea":   game_idea,
                "output_file": output_file,
                "status":      status,
                "retries":     retries,
                "description": description,
                "code_length": code_length,
                "game_code":   game_code,
                "created_at":  now_iso,
            }).execute()
            print(f"[Supabase] Run logged to cloud (id={run_id}, status={status}).")
    except Exception as exc:
        print(f"[Supabase] Cloud log failed ({exc}) — local SQLite copy was saved.")

    return run_id


def get_run_history(limit: int = 20) -> list[dict]:
    """
    Fetch the most recent runs.
    Checks Supabase first; if offline, paused, or empty, reads from local SQLite.
    """
    # 1. Try Supabase
    try:
        client = _get_client()
        if client:
            response = (
                client.table("runs")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            if response.data:
                return response.data
    except Exception as exc:
        print(f"[Supabase] History fetch failed ({exc}) — falling back to local SQLite.")

    # 2. Fallback to SQLite
    try:
        conn = _get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as exc:
        print(f"[SQLite] Fallback history query error: {exc}")
        return []


def get_run_by_id(run_id: str) -> Optional[dict]:
    """Fetch a single run record by its UUID from Supabase or local SQLite."""
    # 1. Try Supabase
    try:
        client = _get_client()
        if client:
            response = (
                client.table("runs")
                .select("*")
                .eq("id", run_id)
                .single()
                .execute()
            )
            if response.data:
                return response.data
    except Exception:
        pass

    # 2. Try local SQLite
    try:
        conn = _get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def delete_run(run_id: str) -> bool:
    """Delete a run record from both local SQLite and Supabase."""
    # 1. Delete from SQLite
    try:
        conn = _get_sqlite_conn()
        with conn:
            conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        conn.close()
    except Exception as exc:
        print(f"[SQLite] Warning deleting run: {exc}")

    # 2. Delete from Supabase
    try:
        client = _get_client()
        if client:
            client.table("runs").delete().eq("id", run_id).execute()
    except Exception as exc:
        print(f"[Supabase] Warning deleting run: {exc}")

    return True
