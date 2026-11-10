#!/bin/sh
# Explicitly restores an existing backup. Requires user to provide a backup basename.
set -eu
cd "$(dirname "$0")/.."
: "${FRIDGE_IMAGE:?Set FRIDGE_IMAGE to the compatible image to run}"
[ "$#" -eq 2 ] && [ "$2" = '--confirm-data-loss' ] || { echo 'Usage: ./scripts/restore.sh BACKUP_FILENAME --confirm-data-loss' >&2; exit 1; }
case "$1" in *[!a-zA-Z0-9._-]*|''|.|..) echo 'Use a backup filename from the backup directory, without a path.' >&2; exit 1;; esac
if ! mkdir .deploy-lock 2>/dev/null; then echo 'An update or restore is running, or a stale .deploy-lock needs inspection.' >&2; exit 1; fi
trap 'rmdir .deploy-lock' EXIT
trap 'exit 130' HUP INT TERM
echo 'Stopping application. The restored database replaces current data; current database files will be archived in the data volume.'
docker compose stop fridge
docker compose run --rm --no-deps --entrypoint python fridge -m app.restore "/backups/$1" /data/fridge.db
echo 'Restore completed. Service remains stopped; confirm image compatibility before starting it.'
