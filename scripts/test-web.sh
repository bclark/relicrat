#!/bin/sh
# Fixed disposable target only: no database URL, project, or real data accepted.
set -eu
[ "$#" -eq 0 ] || { echo 'Usage: sh scripts/test-web.sh' >&2; exit 2; }
cd "$(dirname "$0")/.."
docker() { command docker --host unix:///var/run/docker.sock "$@"; }
[ "$(docker info --format '{{.Name}}')" = relicrat-worker ] || {
    echo 'Web integration requires the dedicated relicrat-worker guest engine' >&2
    exit 1
}
run_dir=$(mktemp -d /tmp/relicrat-web.XXXXXXXXXX)
export BUILDX_CONFIG="$run_dir/buildx"
mkdir "$BUILDX_CONFIG"
project=$(basename "$run_dir" | tr '[:upper:].' '[:lower:]-')
compose() { docker compose -p "$project" -f infra/docker/compose.web-test.yaml "$@"; }
cleanup() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$result" -ne 0 ]; then compose logs --no-color || true; fi
    compose down --volumes --remove-orphans --rmi local || result=1
    for kind in container volume network image; do
        case "$kind" in
            container) remaining=$(docker ps -aq --filter "label=com.docker.compose.project=$project") ;;
            volume) remaining=$(docker volume ls -q --filter "label=com.docker.compose.project=$project") ;;
            network) remaining=$(docker network ls -q --filter "label=com.docker.compose.project=$project") ;;
            image) remaining=$(docker image ls -q --filter "reference=$project-*") ;;
        esac
        if [ -n "$remaining" ]; then echo "Cleanup failed: $kind for $project" >&2; result=1; fi
    done
    rm -rf -- "$run_dir"
    echo "Web cleanup checked for $project; exit=$result"
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
printf 'Web test project: %s\n' "$project"
compose build api web
compose run --rm --no-deps web npm test
compose run --rm --no-deps web npm run lint
compose up -d --wait db
compose run --rm --no-deps api alembic upgrade head
compose up -d api web
compose exec -T web node tests/browser-api-smoke.mjs seed
# Recreate the API container: photo persistence must come from the media volume.
compose rm --stop --force api
compose up -d api
compose exec -T web node tests/browser-api-smoke.mjs verify
