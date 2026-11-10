#!/bin/sh
# Run from the deployment directory. Never automatically restore a database.
set -eu
cd "$(dirname "$0")/.."
FRIDGE_IMAGE=${FRIDGE_IMAGE:-ghcr.io/heathkang/smart-fridge:latest}
case "$FRIDGE_IMAGE" in
  ghcr.io/heathkang/smart-fridge:latest) ;;
  ghcr.io/heathkang/smart-fridge:*) tag=${FRIDGE_IMAGE##*:}; case "$tag" in *[!0-9a-f]*|'') echo 'Use latest or a full 40-character commit SHA tag.' >&2; exit 1;; esac; [ "${#tag}" -eq 40 ] || { echo 'Use latest or a full 40-character commit SHA tag.' >&2; exit 1; } ;;
  *) echo 'Use the latest or a SHA-tagged smart-fridge image.' >&2; exit 1;;
esac
export FRIDGE_IMAGE
requested_image=$FRIDGE_IMAGE
mkdir -p .deploy-state
if ! mkdir .deploy-lock 2>/dev/null; then echo 'Another update is running, or a stale .deploy-lock needs inspection.' >&2; exit 1; fi
trap 'rmdir .deploy-lock' EXIT
trap 'exit 130' HUP INT TERM
container=$(docker compose ps -q fridge)
[ -n "$container" ] || { echo 'No running existing service. Follow the documented first-install or recovery procedure.' >&2; exit 1; }
[ "$(docker inspect -f '{{.State.Running}}' "$container")" = true ] || { echo 'Existing service is not running; investigate before updating.' >&2; exit 1; }
old_image=$(docker inspect -f '{{.Image}}' "$container")
docker compose pull fridge
# Pin the pulled image for both backup and deployment even if latest changes.
FRIDGE_IMAGE=$(docker image inspect -f '{{.Id}}' "$requested_image")
export FRIDGE_IMAGE
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_file="/backups/pre-update-${stamp}-$$.sqlite"
docker compose run --rm --no-deps --entrypoint python fridge -m app.backup /data/fridge.db "$backup_file"
printf '%s\n' "$old_image" > .deploy-state/previous-image-id
printf '%s\n' "$backup_file" > .deploy-state/pre-update-backup
printf '%s\n' "$requested_image" > .deploy-state/requested-image
printf 'Previous image: %s\nNew image: %s\nBackup: %s\n' "$old_image" "$FRIDGE_IMAGE" "$backup_file"
docker compose up -d --no-build --no-deps fridge
container=$(docker compose ps -q fridge)
count=0
while [ "$count" -lt 18 ]; do
  status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")
  if [ "$status" = healthy ]; then
    printf '%s\n' "$FRIDGE_IMAGE" > .deploy-state/current-image
    echo 'Update completed and health check passed.'
    exit 0
  fi
  if [ "$status" = unhealthy ] || [ "$status" = exited ]; then break; fi
  count=$((count + 1))
  sleep 5
done
echo 'Update failed or health check timed out. Service and database require inspection; see README recovery instructions. Do not restart an older image against a migrated database without checking compatibility.' >&2
exit 1
