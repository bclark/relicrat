"""Send current API sources to an SSH host and run the disposable test stack.

Usage: python3 scripts/test-api-remote.py technodrome [pytest arguments...]
Requires only local Python 3.11+, Git, SSH, and remote Docker Compose.
"""
import hashlib
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else "technodrome"
    if host.startswith("-"):
        raise SystemExit("SSH host must not be an option")
    root = Path(__file__).resolve().parent.parent
    if host == "relicrat-worker":
        ssh = [sys.executable, str(root / "scripts/worker-ssh.py")]
    else:
        ssh = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "ConnectTimeout=10", host]
    files = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
         "apps/api", "infra/docker/compose.test.yaml", "scripts/test-api.sh"], cwd=root,
    ).split(b"\0")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    results = root / ".harness-results" / run_id
    results.mkdir(parents=True)
    with tempfile.TemporaryFile() as archive:
        with tarfile.open(fileobj=archive, mode="w") as bundle:
            for name in files:
                if not name:
                    continue
                relative = Path(name.decode())
                path = root / relative
                if path.is_symlink():
                    raise SystemExit(f"Refusing to transfer symlink: {relative}")
                if path.is_file():
                    bundle.add(path, arcname=str(relative), recursive=False)
        archive.seek(0)
        digest = hashlib.file_digest(archive, "sha256").hexdigest()
        archive.seek(0)
        remote = subprocess.check_output(
            ssh + ["mktemp -d /tmp/relicrat-test.XXXXXXXXXX"], text=True,
        ).strip()
        if not re.fullmatch(r"/tmp/relicrat-test\.[A-Za-z0-9]+", remote):
            raise SystemExit("Unexpected remote temporary path; refusing to proceed")
        try:
            subprocess.run(ssh + [f"tar -xf - -C {shlex.quote(remote)}"], stdin=archive, check=True)
            command = shlex.join(["sh", "scripts/test-api.sh", *sys.argv[2:]])
            with (results / "run.log").open("w") as log:
                stamp = f"Host: {host}\nSnapshot SHA256: {digest}\nCommand: {command}\n"
                print(stamp, flush=True)
                log.write(stamp)
                with subprocess.Popen(
                    ssh + [f"cd {shlex.quote(remote)} && {command}"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                ) as process:
                    for line in process.stdout:
                        print(line, end="", flush=True)
                        log.write(line)
                    result = process.wait()
                log.write(f"Exit status: {result}\n")
            print(f"Evidence: {results / 'run.log'}", flush=True)
            return result
        finally:
            subprocess.run(ssh + [f"rm -rf -- {shlex.quote(remote)}"], check=True)


if __name__ == "__main__":
    sys.exit(main())
