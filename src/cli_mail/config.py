"""Configuration management — reads/writes ~/.config/cli-mail/config.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from cli_mail.models import AccountConfig

CONFIG_DIR = Path.home() / ".config" / "cli-mail"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def _escape_toml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def save_config(config: dict) -> None:
    # We serialize TOML manually because Python's tomllib is read-only and
    # adding tomli-w as a dependency just for config writes isn't worth it.
    ensure_config_dir()
    lines: list[str] = []
    if "default_account" in config:
        lines.append(f'default_account = "{config["default_account"]}"')
        lines.append("")
    for key, acct in config.get("accounts", {}).items():
        lines.append(f'[accounts."{_escape_toml(key)}"]')
        for k, v in acct.items():
            if isinstance(v, bool):
                lines.append(f"{k} = {'true' if v else 'false'}")
            elif isinstance(v, int):
                lines.append(f"{k} = {v}")
            else:
                lines.append(f'{k} = "{_escape_toml(str(v))}"')
        lines.append("")
    CONFIG_FILE.write_text("\n".join(lines) + "\n")


def get_account(name: str | None = None) -> AccountConfig | None:
    """Load an account by name, falling back to the default or first available."""
    config = load_config()
    accounts = config.get("accounts", {})
    if not accounts:
        return None
    if name is None:
        name = config.get("default_account", next(iter(accounts)))
    acct = accounts.get(name)
    if acct is None:
        return None
    return AccountConfig(
        email=acct["email"],
        imap_host=acct["imap_host"],
        imap_port=acct.get("imap_port", 993),
        smtp_host=acct.get("smtp_host", ""),
        smtp_port=acct.get("smtp_port", 587),
        use_ssl=acct.get("use_ssl", True),
        name=name,
    )


def save_account(account: AccountConfig) -> None:
    config = load_config()
    if "accounts" not in config:
        config["accounts"] = {}
    config["accounts"][account.name] = {
        "email": account.email,
        "imap_host": account.imap_host,
        "imap_port": account.imap_port,
        "smtp_host": account.smtp_host,
        "smtp_port": account.smtp_port,
        "use_ssl": account.use_ssl,
    }
    if "default_account" not in config:
        config["default_account"] = account.name
    save_config(config)


def delete_account(name: str) -> None:
    config = load_config()
    accounts = config.get("accounts", {})
    accounts.pop(name, None)
    if config.get("default_account") == name:
        config["default_account"] = next(iter(accounts), "")
    config["accounts"] = accounts
    save_config(config)


def list_accounts() -> list[str]:
    config = load_config()
    return list(config.get("accounts", {}).keys())


# Well-known provider IMAP/SMTP settings keyed by email domain.
# ProtonMail uses localhost because it requires ProtonMail Bridge, a local
# daemon that exposes standard IMAP/SMTP on non-standard ports.
PROVIDER_DEFAULTS: dict[str, dict[str, str | int]] = {
    "gmail.com": {"imap_host": "imap.gmail.com", "smtp_host": "smtp.gmail.com"},
    "googlemail.com": {"imap_host": "imap.gmail.com", "smtp_host": "smtp.gmail.com"},
    "outlook.com": {"imap_host": "outlook.office365.com", "smtp_host": "smtp.office365.com"},
    "hotmail.com": {"imap_host": "outlook.office365.com", "smtp_host": "smtp.office365.com"},
    "yahoo.com": {"imap_host": "imap.mail.yahoo.com", "smtp_host": "smtp.mail.yahoo.com"},
    "icloud.com": {"imap_host": "imap.mail.me.com", "smtp_host": "smtp.mail.me.com"},
    "fastmail.com": {"imap_host": "imap.fastmail.com", "smtp_host": "smtp.fastmail.com"},
    "protonmail.com": {"imap_host": "127.0.0.1", "imap_port": 1143, "smtp_host": "127.0.0.1", "smtp_port": 1025},
}


def guess_provider(email: str) -> dict[str, str | int]:
    parts = email.split("@")
    if len(parts) != 2:
        return {}
    return PROVIDER_DEFAULTS.get(parts[1].lower(), {})
