"""Credential storage using the system keychain via keyring."""

from __future__ import annotations

SERVICE_NAME = "cli-mail"

_keyring_available = True
try:
    import keyring
except ImportError:
    _keyring_available = False


def store_password(account_name: str, password: str) -> bool:
    if not _keyring_available:
        return False
    try:
        keyring.set_password(SERVICE_NAME, account_name, password)
        return True
    except Exception:
        return False


def get_password(account_name: str) -> str | None:
    if not _keyring_available:
        return None
    try:
        return keyring.get_password(SERVICE_NAME, account_name)
    except Exception:
        return None


def delete_password(account_name: str) -> bool:
    if not _keyring_available:
        return False
    try:
        keyring.delete_password(SERVICE_NAME, account_name)
        return True
    except Exception:
        return False
