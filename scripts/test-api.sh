#!/bin/sh
# Run only against the disposable stack defined here, never a supplied database.
set -eu
cd "$(dirname "$0")/.."
project="relicrat-test-$(date +%s)-$$"
compose() {
    docker compose --project-name "$project" --file infra/docker/compose.test.yaml "$@"
}
cleanup() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$result" -ne 0 ]; then
        compose logs --no-color db || true
    fi
    compose down --volumes --remove-orphans --rmi local || result=1
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
echo "Test project: $project"
compose build tests
compose up --detach --wait db
compose run --rm --no-deps tests sh -ec '
    python --version
    python -m pip freeze
    alembic upgrade head
    python -m pytest -v "$@"
    alembic downgrade base
    alembic upgrade head
' sh "$@"
