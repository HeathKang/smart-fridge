import sqlite3
import pytest
from app.backup import backup
from app.migrations import migrate


def test_legacy_migration_and_verified_backup(tmp_path):
    db = tmp_path / 'fridge.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, quantity TEXT NOT NULL, storage TEXT NOT NULL, delivered TEXT NOT NULL, expires TEXT NOT NULL, estimated INTEGER NOT NULL DEFAULT 0)')
        conn.execute("INSERT INTO items VALUES (1, '菠菜', '1', '冷藏', '2026-01-01', '2026-01-03', 0)")
    migrate(db)
    migrate(db)
    snapshot = tmp_path / 'backup.sqlite'
    backup(db, snapshot)
    with sqlite3.connect(snapshot) as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 1
        assert conn.execute('SELECT name FROM items').fetchone()[0] == '菠菜'
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    with pytest.raises(FileExistsError):
        backup(db, snapshot)


def test_unknown_or_newer_schema_fails_without_changing_data(tmp_path):
    db = tmp_path / 'fridge.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE items (id INTEGER PRIMARY KEY, mystery TEXT)')
        conn.execute("INSERT INTO items VALUES (1, 'keep')")
    with pytest.raises(RuntimeError, match='Unrecognized'):
        migrate(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 0
        assert conn.execute('SELECT mystery FROM items').fetchone()[0] == 'keep'
        conn.execute('PRAGMA user_version = 999')
    with pytest.raises(RuntimeError, match='newer'):
        migrate(db)


def test_existing_history_survives_migration_and_restored_backup(tmp_path):
    db = tmp_path / 'old.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, quantity TEXT NOT NULL, storage TEXT NOT NULL, delivered TEXT NOT NULL, expires TEXT NOT NULL, estimated INTEGER NOT NULL DEFAULT 0)')
        conn.execute('CREATE TABLE handling_events (id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id), outcome TEXT NOT NULL, reason TEXT, handled_at TEXT NOT NULL, restored_at TEXT)')
        conn.execute("INSERT INTO items VALUES (1,'豆腐','一盒','冷藏','2026-01-01','2026-01-04',1)")
        conn.execute("INSERT INTO handling_events VALUES (1,1,'丢弃了','过期','2026-01-05T00:00:00Z',NULL)")
    before = tmp_path / 'before.sqlite'
    backup(db, before)
    migrate(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT outcome, reason FROM handling_events').fetchone() == ('丢弃了', '过期')
        conn.execute("UPDATE items SET name='改变'")
    restored = tmp_path / 'restored.sqlite'
    backup(before, restored)
    migrate(restored)
    with sqlite3.connect(restored) as conn:
        assert conn.execute('SELECT name FROM items').fetchone()[0] == '豆腐'
        assert conn.execute('SELECT count(*) FROM handling_events').fetchone()[0] == 1


def test_restore_preserves_replaced_database(tmp_path):
    from app.restore import restore
    database = tmp_path / 'fridge.db'
    with sqlite3.connect(database) as conn:
        conn.execute('CREATE TABLE food (name TEXT)')
        conn.execute("INSERT INTO food VALUES ('original')")
    snapshot = tmp_path / 'snapshot.sqlite'
    backup(database, snapshot)
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE food SET name='after backup'")
    archive = restore(snapshot, database)
    with sqlite3.connect(database) as conn:
        assert conn.execute('SELECT name FROM food').fetchone()[0] == 'original'
    with sqlite3.connect(archive / 'fridge.db') as conn:
        assert conn.execute('SELECT name FROM food').fetchone()[0] == 'after backup'


def test_failed_migration_rolls_back_schema_version(tmp_path):
    db = tmp_path / 'bad.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, quantity TEXT NOT NULL, storage TEXT NOT NULL, delivered TEXT NOT NULL, expires TEXT NOT NULL, estimated INTEGER NOT NULL DEFAULT 0)')
        conn.execute('CREATE TABLE handling_events (id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL, outcome TEXT NOT NULL, reason TEXT, handled_at TEXT NOT NULL, restored_at TEXT)')
        conn.executemany("INSERT INTO handling_events VALUES (?,1,'吃完了',NULL,'2026-01-01',NULL)", [(1,), (2,)])
    with pytest.raises(sqlite3.IntegrityError):
        migrate(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM handling_events').fetchone()[0] == 2
