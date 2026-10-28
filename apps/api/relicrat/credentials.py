"""Standard-library owner password hashing; no application imports for setup CLI."""
import hashlib
import hmac
import os
import re
import secrets

FORMAT = re.compile(r'^scrypt\$([0-9a-f]{32})\$([0-9a-f]{128})$')


def derive(password, salt):
    return hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2**17, r=8, p=1,
                          maxmem=256 * 1024 * 1024, dklen=64)


def hash_password(password):
    if not 15 <= len(password) <= 256:
        raise ValueError('Use a password between 15 and 256 characters')
    salt = secrets.token_bytes(16)
    return 'scrypt$' + salt.hex() + '$' + derive(password, salt).hex()


def owner_config():
    encoded = os.getenv('RELICRAT_OWNER_PASSWORD_HASH', '')
    match = FORMAT.fullmatch(encoded)
    secret = os.getenv('RELICRAT_SESSION_SECRET', '')
    if not match or not re.fullmatch(r'[0-9a-f]{64}', secret):
        raise ValueError('Owner access is not configured')
    fingerprint = hmac.new(bytes.fromhex(secret), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded, fingerprint


def verify_password(password, encoded):
    match = FORMAT.fullmatch(encoded)
    if not match:
        raise ValueError('Invalid password hash')
    return hmac.compare_digest(derive(password, bytes.fromhex(match[1])), bytes.fromhex(match[2]))
