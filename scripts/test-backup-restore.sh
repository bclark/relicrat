#!/bin/sh
# No database URL, archive, project name, or restore target is accepted.
set -eu
cd "$(dirname "$0")/.."
case "${1:-}" in
    '') mode=verify ;;
    --missing-media) mode=missing ;;
    --corrupt-media) mode=corrupt ;;
    *) echo 'Usage: sh scripts/test-backup-restore.sh [--missing-media|--corrupt-media]' >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || exit 2
: "${BUILDX_CONFIG:?Use the operator-provided disposable BUILDX_CONFIG}"
[ -d "$BUILDX_CONFIG" ] && [ -w "$BUILDX_CONFIG" ]
# Never follow a supplied remote Docker host/context. This guest owns this socket.
docker() { command docker --host unix:///var/run/docker.sock "$@"; }
[ "$(docker info --format '{{.Name}}')" = relicrat-worker ] || {
    echo 'Recovery rehearsal requires the dedicated relicrat-worker guest engine' >&2
    exit 1
}
# mktemp supplies an unpredictable, exclusively allocated run identifier.
run_dir=$(mktemp -d /tmp/relicrat-recovery.XXXXXXXXXX)
project=$(basename "$run_dir" | tr '[:upper:].' '[:lower:]-')
compose() {
    docker compose --project-name "$project" --file infra/docker/compose.recovery.yaml "$@"
}
cleanup() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$result" -ne 0 ]; then
        compose logs --no-color || true
    fi
    compose down --volumes --remove-orphans --rmi local || result=1
    # Prove that this project's resources are gone, without touching other runs.
    for kind in container volume network image; do
        case "$kind" in
            container) remaining=$(docker ps -aq --filter "label=com.docker.compose.project=$project") ;;
            volume) remaining=$(docker volume ls -q --filter "label=com.docker.compose.project=$project") ;;
            network) remaining=$(docker network ls -q --filter "label=com.docker.compose.project=$project") ;;
            image) remaining=$(docker image ls -q --filter "reference=$project-*") ;;
        esac
        if [ -n "$remaining" ]; then
            echo "Cleanup failed: $kind resources remain for $project" >&2
            result=1
        fi
    done
    rmdir "$run_dir" || result=1
    echo "Cleanup checked for $project; exit=$result"
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
echo "Recovery project: $project; mode=$mode"
echo "Source revision: $(git rev-parse HEAD); local changes:"
git status --short
compose build source-api restore-api
compose up --detach --wait source-db
compose run --rm --no-deps source-api sh -ec 'alembic upgrade head; python /rehearsal/backup-restore.py seed'
echo 'Writes quiesced: seeding process exited; no API server or other writer exists.'
compose exec -T source-db pg_dump -U relicrat_recovery -d relicrat_recovery --format=custom --file=/evidence/database.dump
compose run --rm --no-deps source-api python /rehearsal/backup-restore.py archive
# Destroy source DB tmpfs and its media before creating the restore stack.
compose rm --stop --force source-db
docker volume rm "${project}_source-media"
echo 'Source database container and source media volume removed.'
compose up --detach --wait restore-db
compose exec -T restore-db pg_restore -U relicrat_recovery -d relicrat_recovery --exit-on-error --no-owner --no-privileges /evidence/database.dump
compose run --rm --no-deps restore-api python /rehearsal/backup-restore.py extract
if [ "$mode" != verify ]; then
    compose run --rm --no-deps restore-api python /rehearsal/backup-restore.py "$mode"
fi
# Always run identical strict verification, including for deliberate media damage.
compose run --rm --no-deps restore-api python /rehearsal/backup-restore.py verify
echo 'Recovery verification passed.'
