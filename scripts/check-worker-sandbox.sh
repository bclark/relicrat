#!/bin/sh
# Run inside the dedicated guest. This starts commands, not a coding agent.
set -eu
command -v bwrap
probe=$(mktemp -d "$HOME/relicrat-sandbox.XXXXXXXXXX")
trap 'rm -rf -- "$probe"' EXIT
mkdir "$probe/workspace" "$probe/outside"
printf 'untouched' > "$probe/outside/marker"
cd "$probe/workspace"
codex sandbox \
    -c 'sandbox_mode="workspace-write"' \
    -c 'sandbox_workspace_write.network_access=true' \
    -- python3 - "$probe/outside/marker" <<'PY'
import errno
from pathlib import Path
import subprocess
import sys

Path('workspace-proof').write_text('allowed')
assert Path('workspace-proof').read_text() == 'allowed'
try:
    Path(sys.argv[1]).write_text('forbidden')
except OSError as error:
    if error.errno not in (errno.EACCES, errno.EPERM, errno.EROFS):
        raise
else:
    raise SystemExit('FAIL: sandbox permitted a direct write outside its workspace')
subprocess.run(['docker', 'info', '--format', 'Sandbox Docker engine: {{.Name}}'], check=True)
print('Sandbox preflight passed: workspace writable, outside write denied, guest Docker reachable')
PY
test "$(cat "$probe/outside/marker")" = untouched
