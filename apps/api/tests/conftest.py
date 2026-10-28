"""Synthetic owner credentials only; no production bypass or weakened hashing."""
import pytest
from relicrat.credentials import hash_password

PASSWORD = 'synthetic-only-owner-password'
PASSWORD_HASH = hash_password(PASSWORD)
SECRET = '17' * 32


@pytest.fixture(autouse=True)
def owner_configuration(monkeypatch):
    monkeypatch.setenv('RELICRAT_OWNER_PASSWORD_HASH', PASSWORD_HASH)
    monkeypatch.setenv('RELICRAT_SESSION_SECRET', SECRET)
