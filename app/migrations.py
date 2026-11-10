"""Ordered SQLite schema migrations. Never change a migration after release."""
import sqlite3
from pathlib import Path

VERSION = 1
ITEM_COLUMNS = {'id', 'name', 'quantity', 'storage', 'delivered', 'expires', 'estimated'}
EVENT_COLUMNS = {'id', 'item_id', 'outcome', 'reason', 'handled_at', 'restored_at'}


def migrate(path: Path) -> None:
    with sqlite3.connect(path, timeout=30, isolation_level=None) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version > VERSION:
                raise RuntimeError(f'Database version {version} is newer than supported version {VERSION}')
            if version == 0:
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                if tables - {'items', 'handling_events'} or ('handling_events' in tables and 'items' not in tables):
                    raise RuntimeError('Unrecognized legacy database; refusing migration')
                if 'items' in tables:
                    columns = {r[1] for r in db.execute('PRAGMA table_info(items)')}
                    if columns != ITEM_COLUMNS:
                        raise RuntimeError('Unrecognized legacy items schema; refusing migration')
                else:
                    db.execute('CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, quantity TEXT NOT NULL, storage TEXT NOT NULL, delivered TEXT NOT NULL, expires TEXT NOT NULL, estimated INTEGER NOT NULL DEFAULT 0)')
                if 'handling_events' in tables:
                    columns = {r[1] for r in db.execute('PRAGMA table_info(handling_events)')}
                    if columns != EVENT_COLUMNS:
                        raise RuntimeError('Unrecognized legacy handling_events schema; refusing migration')
                else:
                    db.execute('CREATE TABLE handling_events (id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id), outcome TEXT NOT NULL, reason TEXT, handled_at TEXT NOT NULL, restored_at TEXT)')
                db.execute('CREATE UNIQUE INDEX IF NOT EXISTS one_active_handling ON handling_events(item_id) WHERE restored_at IS NULL')
                db.execute('PRAGMA user_version = 1')
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK')
            raise
