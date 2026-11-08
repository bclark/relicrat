# Private Linux installation with Docker Compose

This first install target is a dedicated Ubuntu 24.04 host with rootful Docker
Engine 28 or later, Docker Compose v2, Git, socat, and Python 3.11 or later. Use a
reviewed full commit SHA as the release pin. The application builds from that
checkout and tags its images with the same SHA. Retain the built images for
offline restarts. Rebuilding can fetch newer dependencies allowed by the source.

## Install

From a fresh checkout dedicated to this instance, replace the placeholder with
the reviewed release commit. Use the same Compose project name throughout.

```sh
git clone https://github.com/bclark/relicrat.git
cd relicrat
git checkout --detach YOUR_REVIEWED_FULL_COMMIT_SHA
export RELICRAT_RELEASE="$(git rev-parse HEAD)"
python3 scripts/configure-owner.py --origin http://127.0.0.1:3000 \
  --allow-loopback-http --generate-database-password --output .env

compose() { docker compose -p relicrat -f compose.linux.yaml "$@"; }
docker pull postgres:17-alpine
compose build --pull
compose up -d --wait db
compose run --rm --no-deps api alembic upgrade head
compose up -d --no-build --wait
```

Run this relay on the Linux host in a separate terminal from the checkout,
with the same release export and `compose` function defined above. It binds to
loopback and forwards to the current web container. Start it again after
recreating the web container so it uses the current address.

```sh
web_ip="$(docker inspect "$(compose ps -q web)" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"
test -n "$web_ip" && socat TCP4-LISTEN:3000,bind=127.0.0.1,reuseaddr,fork "TCP4:$web_ip:3000"
```

Open `http://127.0.0.1:3000` and sign in. All three containers communicate on
the internal Docker network, which blocks runtime internet access. Database
records and photos live in the project's named volumes. Keep the generated
mode-0600 `.env` private and preserve it across upgrades. Ordinary
`compose down` keeps the volumes. Avoid the volume-removal option.

To use a desktop browser on another machine, forward the loopback port over
SSH and keep the same browser origin.

```sh
ssh -N -L 127.0.0.1:3000:127.0.0.1:3000 YOUR_LINUX_HOST
```

For an Android phone connected to that desktop over USB, enable Android
debugging and run `adb reverse tcp:3000 tcp:3000`, then open the same loopback
URL in the phone browser. The desktop SSH tunnel must stay open when the Linux
host is remote. The automated install test uses desktop and phone browser
profiles on a clean Linux runner.

## Reset the owner password

Create a new file with the same origin. Preserve the original database
password and swap the owner file privately while the app is stopped. The new
owner configuration revokes existing sessions and agent access.

```sh
umask 077
python3 scripts/configure-owner.py --origin http://127.0.0.1:3000 \
  --allow-loopback-http --output .env.owner.next
sed -n '/^POSTGRES_PASSWORD=/p' .env >> .env.owner.next
compose stop web api
mv .env.owner.next .env
compose up -d --no-build --wait
```

## Before upgrading

Keep the old checkout and its images available. With the current release and
`.env` selected, make a new offline backup. Confirm the Docker engine name and
project refer to your instance, and choose a new directory under a private
backup parent. The command pauses API and web writers and restarts them.

```sh
docker --host unix:///var/run/docker.sock info --format '{{.Name}}'
mkdir -m 700 -p backups
python3 scripts/backup.py create --engine YOUR_CONFIRMED_ENGINE_NAME \
  --compose compose.linux.yaml --project relicrat --offline-confirmed \
  backups/NEW_BACKUP_DIRECTORY
```

Check for `manifest.json` and confirm the app is reachable before proceeding.
Retain the backup and matching images and source. See the existing operator
guide for [backup and restore details](backup-restore.md). Keep the PostgreSQL
major version fixed for application upgrades.

Fetch and check out the new reviewed commit, export its full SHA as above,
and build the new images. Stop web and API before migrating. Run
`compose run --rm --no-deps api alembic upgrade head` and then
`compose up -d --no-build --wait`. If a migration fails, keep the writers
stopped and inspect it before reopening the app.
