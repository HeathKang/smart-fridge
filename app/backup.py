"""Create an integrity-checked SQLite online backup without overwriting a file."""
import argparse
import os
import sqlite3
from pathlib import Path


def backup(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f'Database does not exist: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement of an existing backup.
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Backup integrity check failed')
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    backup(args.source, args.destination)
    print(f'Backup verified: {args.destination}')
