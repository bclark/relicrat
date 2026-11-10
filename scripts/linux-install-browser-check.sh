#!/bin/sh
# Run the browser workflow against the disposable Ubuntu CI install.
set -eu
test "${RELICRAT_TEST_LINUX_INSTALL:-}" = 1
web_ip="$(docker inspect "$(docker compose ps -q web)" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"
test -n "$web_ip"
socat TCP4-LISTEN:3000,bind=127.0.0.1,reuseaddr,fork "TCP4:$web_ip:3000" &
relay_pid=$!
trap 'kill "$relay_pid" 2>/dev/null || true' EXIT
curl -fsS --retry 20 --retry-connrefused --retry-delay 1 --max-time 5 http://127.0.0.1:3000/login -o /dev/null
if [ "$#" -gt 0 ]; then
    node "$@"
else
    node --test apps/web/tests/linux-install.browser.mjs
fi
