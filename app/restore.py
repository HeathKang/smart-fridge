"""Restore a verified backup while the application is stopped."""
import argparse
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from app.backup import backup


def restore(snapshot: Path, database: Path) -> Path:
    if not database.parent.is_dir():
        raise FileNotFoundError('Database directory is missing')
    archive = database.parent / ('before-restore-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    archive.mkdir(mode=0o700)
    temporary = Path(tempfile.mkdtemp(prefix='.restore-', dir=database.parent))
    staged = temporary / database.name
    moved = []
    try:
        backup(snapshot, staged)
        for suffix in ('', '-wal', '-shm'):
            source = Path(str(database) + suffix)
            if source.exists():
                target = archive / source.name
                os.rename(source, target)
                moved.append((source, target))
        os.rename(staged, database)
    except BaseException:
        for source, target in reversed(moved):
            os.rename(target, source)
        raise
    finally:
        temporary.rmdir()
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('database', type=Path)
    args = parser.parse_args()
    print(f'Previous database files preserved in: {restore(args.snapshot, args.database)}')
