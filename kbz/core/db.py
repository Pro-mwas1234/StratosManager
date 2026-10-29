"""Thin SQLite gateway + forward-only migration runner.

Design chokepoint: every repository query goes through `Database.tenant_rows/tenant_insert`
helpers that inject tenant_id, so cross-tenant leakage is structurally hard.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .errors import ConflictError, NotFoundError

DEFAULT_DB = os.environ.get("KBZ_DB", str(Path(__file__).resolve().parents[2] / "data" / "kbz.db"))


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def month_key(ts: str | None = None) -> str:
    ts = ts or now_iso()
    return ts[:7]  # YYYY-MM


def new_id(prefix: str = "") -> str:
    raw = uuid.uuid4().hex[:10]
    return f"{prefix}{raw}" if prefix else raw


def token_string() -> str:
    return "kbz_" + secrets.token_urlsafe(32)


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or DEFAULT_DB
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    # -- low level ---------------------------------------------------------
    def exec(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    # -- tenant-scoped chokepoints ----------------------------------------
    def tenant_insert(self, table: str, tenant_id: str, data: dict) -> str:
        rid = data.get("id") or new_id(table[:3])
        row = {"id": rid, "tenant_id": tenant_id, "created_at": now_iso(), **data, "id": rid}
        cols = ", ".join(row.keys())
        marks = ", ".join("?" for _ in row)
        try:
            self.exec(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(_jsonable(v) for v in row.values()))
        except sqlite3.IntegrityError as e:
            raise ConflictError(f"duplicate value in {table}: {e}") from e
        return rid

    def tenant_rows(self, table: str, tenant_id: str, where: str = "", params: tuple = (),
                    order: str = "created_at DESC", limit: int | None = None) -> list[dict]:
        sql = f"SELECT * FROM {table} WHERE tenant_id=?"
        p: tuple = (tenant_id,)
        if where:
            sql += f" AND ({where})"
            p += params
        sql += f" ORDER BY {order}"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self.query(sql, p)

    def tenant_get(self, table: str, tenant_id: str, row_id: str) -> dict:
        row = self.one(f"SELECT * FROM {table} WHERE tenant_id=? AND id=?", (tenant_id, row_id))
        if not row:
            raise NotFoundError(f"{table} '{row_id}' not found")
        return row

    def tenant_update(self, table: str, tenant_id: str, row_id: str, data: dict) -> dict:
        self.tenant_get(table, tenant_id, row_id)  # existence + scope check
        sets = ", ".join(f"{k}=?" for k in data)
        vals = tuple(_jsonable(v) for v in data.values())
        self.exec(f"UPDATE {table} SET {sets}, updated_at=? WHERE tenant_id=? AND id=?",
                  vals + (now_iso(), tenant_id, row_id))
        return self.tenant_get(table, tenant_id, row_id)

    def tenant_delete(self, table: str, tenant_id: str, row_id: str) -> None:
        self.tenant_get(table, tenant_id, row_id)
        self.exec(f"DELETE FROM {table} WHERE tenant_id=? AND id=?", (tenant_id, row_id))

    def close(self):
        with self._lock:
            self._conn.close()


def _jsonable(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    if isinstance(v, bool):
        return int(v)
    return v


# ---------------------------------------------------------------------------
# Migrations: numbered SQL files under kbz/core/migrations/*.sql
# ---------------------------------------------------------------------------
MIG_DIR = Path(__file__).resolve().parent / "migrations"


def run_migrations(db: Database) -> list[str]:
    db.exec("""CREATE TABLE IF NOT EXISTS _migrations(
                 name TEXT PRIMARY KEY, applied_at TEXT)""")
    done = {r["name"] for r in db.query("SELECT name FROM _migrations")}
    applied = []
    for f in sorted(MIG_DIR.glob("*.sql")):
        if f.name in done:
            continue
        sql = f.read_text()
        with db._lock:
            db._conn.executescript(sql)
            db._conn.execute("INSERT INTO _migrations(name, applied_at) VALUES (?,?)",
                             (f.name, now_iso()))
            db._conn.commit()
        applied.append(f.name)
    return applied
