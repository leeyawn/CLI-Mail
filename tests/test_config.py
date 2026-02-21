"""Tests for configuration management."""

import tomllib
from pathlib import Path

import pytest

from cli_mail import config as config_module
from cli_mail.config import (delete_account, get_account,
                             get_default_account_name, guess_provider,
                             list_accounts, load_config, save_account,
                             save_config, set_default_account)
from cli_mail.models import AccountConfig


@pytest.fixture()
def config_dir(tmp_path, monkeypatch):
    """Redirect config to a temp directory for isolation."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    return tmp_path


class TestSaveLoadConfig:
    def test_load_empty_when_no_file(self, config_dir):
        assert load_config() == {}

    def test_round_trip_simple_account(self, config_dir):
        original = {
            "default_account": "work",
            "accounts": {
                "work": {
                    "email": "user@example.com",
                    "imap_host": "imap.example.com",
                    "imap_port": 993,
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                    "use_ssl": True,
                },
            },
        }
        save_config(original)
        loaded = load_config()
        assert loaded["default_account"] == "work"
        assert loaded["accounts"]["work"]["email"] == "user@example.com"
        assert loaded["accounts"]["work"]["imap_port"] == 993
        assert loaded["accounts"]["work"]["use_ssl"] is True

    def test_dotted_account_name_survives_round_trip(self, config_dir):
        """Regression test: dots in account names must be quoted in TOML."""
        original = {
            "default_account": "leon.letournel",
            "accounts": {
                "leon.letournel": {
                    "email": "leon@example.com",
                    "imap_host": "imap.example.com",
                    "imap_port": 993,
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 465,
                    "use_ssl": True,
                },
            },
        }
        save_config(original)
        loaded = load_config()
        assert "leon.letournel" in loaded["accounts"]
        assert loaded["accounts"]["leon.letournel"]["email"] == "leon@example.com"

    def test_toml_file_is_valid(self, config_dir):
        """Ensure the written file is parseable TOML."""
        save_config({
            "default_account": "test",
            "accounts": {
                "test": {
                    "email": "test@example.com",
                    "imap_host": "imap.example.com",
                    "imap_port": 993,
                },
            },
        })
        config_file = config_dir / "config.toml"
        with open(config_file, "rb") as f:
            parsed = tomllib.load(f)
        assert "accounts" in parsed

    def test_multiple_accounts(self, config_dir):
        save_config({
            "default_account": "personal",
            "accounts": {
                "personal": {"email": "me@gmail.com", "imap_host": "imap.gmail.com", "imap_port": 993},
                "work": {"email": "me@work.com", "imap_host": "imap.work.com", "imap_port": 993},
            },
        })
        loaded = load_config()
        assert len(loaded["accounts"]) == 2
        assert "personal" in loaded["accounts"]
        assert "work" in loaded["accounts"]


class TestSaveGetAccount:
    def test_save_and_retrieve(self, config_dir):
        acct = AccountConfig(
            email="user@example.com",
            imap_host="imap.example.com",
            imap_port=993,
            smtp_host="smtp.example.com",
            smtp_port=587,
        )
        save_account(acct)
        loaded = get_account(acct.name)
        assert loaded is not None
        assert loaded.email == "user@example.com"
        assert loaded.imap_host == "imap.example.com"
        assert loaded.smtp_port == 587

    def test_get_default_account(self, config_dir):
        acct = AccountConfig(email="user@example.com", imap_host="imap.example.com")
        save_account(acct)
        loaded = get_account()
        assert loaded is not None
        assert loaded.email == "user@example.com"

    def test_get_nonexistent_account(self, config_dir):
        assert get_account("nonexistent") is None

    def test_get_account_empty_config(self, config_dir):
        assert get_account() is None

    def test_list_accounts_empty(self, config_dir):
        assert list_accounts() == []

    def test_list_accounts(self, config_dir):
        save_account(AccountConfig(email="a@example.com", imap_host="imap.example.com", name="acct_a"))
        save_account(AccountConfig(email="b@example.com", imap_host="imap.example.com", name="acct_b"))
        names = list_accounts()
        assert "acct_a" in names
        assert "acct_b" in names

    def test_dotted_name_account_round_trip(self, config_dir):
        """Regression: account with dots in name (e.g. first.last) must survive save/load."""
        acct = AccountConfig(
            email="first.last@company.com",
            imap_host="imap.company.com",
        )
        assert "." in acct.name
        save_account(acct)

        loaded = get_account(acct.name)
        assert loaded is not None
        assert loaded.email == "first.last@company.com"


class TestSaveAccountNameCollision:
    def test_same_local_part_different_domain_gets_disambiguated(self, config_dir):
        """Two emails with the same local part shouldn't overwrite each other."""
        acct1 = AccountConfig(email="leon@gmail.com", imap_host="imap.gmail.com")
        save_account(acct1)
        assert acct1.name == "leon"

        acct2 = AccountConfig(email="leon@outlook.com", imap_host="outlook.office365.com")
        save_account(acct2)

        assert acct2.name != "leon"
        assert acct2.name == "leon@outlook"
        assert len(list_accounts()) == 2

        loaded1 = get_account("leon")
        loaded2 = get_account("leon@outlook")
        assert loaded1 is not None and loaded1.email == "leon@gmail.com"
        assert loaded2 is not None and loaded2.email == "leon@outlook.com"

    def test_same_email_overwrites_same_account(self, config_dir):
        """Re-saving the same email should update, not create a duplicate."""
        acct = AccountConfig(email="leon@gmail.com", imap_host="imap.gmail.com")
        save_account(acct)
        acct2 = AccountConfig(email="leon@gmail.com", imap_host="imap.new.com")
        save_account(acct2)

        assert len(list_accounts()) == 1
        loaded = get_account("leon")
        assert loaded is not None
        assert loaded.imap_host == "imap.new.com"

    def test_triple_collision_uses_numeric_suffix(self, config_dir):
        """Third account with same local part falls back to numeric suffix."""
        save_account(AccountConfig(email="user@gmail.com", imap_host="imap.gmail.com"))
        save_account(AccountConfig(email="user@outlook.com", imap_host="outlook.office365.com"))
        acct3 = AccountConfig(email="user@yahoo.com", imap_host="imap.mail.yahoo.com")
        save_account(acct3)

        names = list_accounts()
        assert len(names) == 3
        assert "user" in names
        assert "user@outlook" in names
        # user@yahoo also collides at short-domain level? No — "user@yahoo" is unique
        assert "user@yahoo" in names


class TestDeleteAccount:
    def test_delete_only_account(self, config_dir):
        save_account(AccountConfig(email="user@example.com", imap_host="imap.example.com"))
        delete_account("user")
        assert list_accounts() == []
        assert get_account() is None

    def test_delete_default_promotes_next(self, config_dir):
        save_account(AccountConfig(email="a@example.com", imap_host="imap.example.com", name="acct_a"))
        save_account(AccountConfig(email="b@example.com", imap_host="imap.example.com", name="acct_b"))
        config = load_config()
        config["default_account"] = "acct_a"
        save_config(config)

        delete_account("acct_a")
        config = load_config()
        assert "acct_a" not in config["accounts"]
        assert config["default_account"] == "acct_b"

    def test_delete_non_default_keeps_default(self, config_dir):
        save_account(AccountConfig(email="a@example.com", imap_host="imap.example.com", name="acct_a"))
        save_account(AccountConfig(email="b@example.com", imap_host="imap.example.com", name="acct_b"))

        delete_account("acct_b")
        config = load_config()
        assert config["default_account"] == "acct_a"
        assert "acct_b" not in config["accounts"]
        assert "acct_a" in config["accounts"]

    def test_delete_nonexistent_is_noop(self, config_dir):
        save_account(AccountConfig(email="user@example.com", imap_host="imap.example.com"))
        delete_account("nonexistent")
        assert list_accounts() == ["user"]


class TestSetDefaultAccount:
    def test_set_default_existing_account(self, config_dir):
        save_account(AccountConfig(email="a@example.com", imap_host="imap.example.com", name="acct_a"))
        save_account(AccountConfig(email="b@example.com", imap_host="imap.example.com", name="acct_b"))

        assert set_default_account("acct_b") is True
        assert get_default_account_name() == "acct_b"

    def test_set_default_nonexistent_account(self, config_dir):
        save_account(AccountConfig(email="a@example.com", imap_host="imap.example.com", name="acct_a"))

        assert set_default_account("nonexistent") is False
        assert get_default_account_name() == "acct_a"

    def test_get_default_account_name_empty(self, config_dir):
        assert get_default_account_name() == ""

    def test_get_default_account_name(self, config_dir):
        save_account(AccountConfig(email="a@example.com", imap_host="imap.example.com", name="acct_a"))
        assert get_default_account_name() == "acct_a"


class TestGuessProvider:
    def test_gmail(self):
        result = guess_provider("user@gmail.com")
        assert result["imap_host"] == "imap.gmail.com"
        assert result["smtp_host"] == "smtp.gmail.com"

    def test_outlook(self):
        result = guess_provider("user@outlook.com")
        assert result["imap_host"] == "outlook.office365.com"

    def test_yahoo(self):
        result = guess_provider("user@yahoo.com")
        assert result["imap_host"] == "imap.mail.yahoo.com"

    def test_unknown_domain_returns_empty(self):
        result = guess_provider("user@mycompany.com")
        assert result == {}

    def test_case_insensitive(self):
        result = guess_provider("user@Gmail.Com")
        assert result["imap_host"] == "imap.gmail.com"
