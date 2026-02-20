"""Credential storage using the system keychain via keyring.

keyring is an optional dependency, when unavailable (e.g. headless servers or
minimal installs), all functions degrade gracefully: stores return False and
lookups return None, causing the app to fall back to interactive password prompts.
"""

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
