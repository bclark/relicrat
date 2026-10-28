"""Interactive owner setup. Writes new ignored configuration; never prints secrets."""
import argparse
import getpass
import os
import re
from pathlib import Path
import secrets
import sys
import warnings
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'apps/api'))
from relicrat.credentials import hash_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True, help='Exact private browser origin, including port')
    parser.add_argument('--allow-loopback-http', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('.env.owner'))
    args = parser.parse_args()
    origin = urlsplit(args.origin)
    if origin.scheme != 'https' and not (args.allow_loopback_http and origin.scheme == 'http' and origin.hostname in ('127.0.0.1', 'localhost', '::1')):
        parser.error('Use HTTPS, or explicitly allow HTTP on loopback only')
    try:
        port = origin.port
    except ValueError:
        parser.error('Use a valid browser port')
    if not origin.hostname or not re.fullmatch(r'[A-Za-z0-9.\-:\[\]]+', origin.netloc) or (port is not None and not 1 <= port <= 65535):
        parser.error('Use a valid private hostname and port')
    if not origin.netloc or origin.username or origin.password or origin.path not in ('', '/') or origin.query or origin.fragment:
        parser.error('Use an origin without credentials, path, query or fragment')
    if args.output.exists():
        parser.error('Output already exists; choose a new file and review rotation before replacing it')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            password = getpass.getpass('New owner password (15–256 characters): ')
            confirmation = getpass.getpass('Confirm owner password: ')
    except (getpass.GetPassWarning, EOFError):
        parser.error('Run setup in an interactive SSH terminal with hidden password input')
    if password != confirmation:
        parser.error('Passwords do not match')
    try:
        encoded = hash_password(password)
    except ValueError as error:
        parser.error(str(error))
    values = {'RELICRAT_OWNER_PASSWORD_HASH': encoded, 'RELICRAT_SESSION_SECRET': secrets.token_hex(32),
              'RELICRAT_WEB_ORIGIN': origin.scheme + '://' + origin.netloc,
              'RELICRAT_ALLOW_LOOPBACK_HTTP': '1' if args.allow_loopback_http else '0'}
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write('# Private owner configuration. Do not commit or share.\n')
        for key, value in values.items():
            stream.write(f"{key}='{value}'\n")
    print(f'Owner configuration saved privately to {args.output.resolve()}')
    print('Keep this file outside backups. Rotation ends all prior sessions after API restart.')


if __name__ == '__main__':
    main()
