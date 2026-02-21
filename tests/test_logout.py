"""Tests for the /account logout command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cli_mail.commands.account import cmd_account_logout
from cli_mail.models import AccountConfig, AppContext


def _make_app(account: AccountConfig | None = None) -> MagicMock:
    app = MagicMock()
    app.ctx = AppContext(account=account, connected=account is not None)
    app._passwords = {}
    if account:
        app._passwords[account.name] = "secret"
    return app


_TEST_ACCOUNT = AccountConfig(
    email="user@example.com",
    imap_host="imap.example.com",
)


class TestCmdLogout:
    def test_no_account_warns(self):
        app = _make_app(account=None)

        with patch("cli_mail.commands.account.ui") as mock_ui:
            cmd_account_logout(app, [])

        mock_ui.print_warning.assert_called_once_with("No account to log out of.")
        app._disconnect.assert_not_called()

    def test_user_declines_confirmation(self):
        app = _make_app(account=_TEST_ACCOUNT)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.delete_password") as mock_del_pw,
            patch("cli_mail.commands.account.delete_account") as mock_del_acct,
        ):
            mock_ui.prompt_confirm.return_value = False
            cmd_account_logout(app, [])

        app._disconnect.assert_not_called()
        mock_del_pw.assert_not_called()
        mock_del_acct.assert_not_called()

    def test_logout_last_account_exits(self):
        app = _make_app(account=_TEST_ACCOUNT)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.delete_password") as mock_del_pw,
            patch("cli_mail.commands.account.delete_account") as mock_del_acct,
            patch("cli_mail.commands.account.list_accounts", return_value=[]),
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_ui.prompt_confirm.return_value = True
            cmd_account_logout(app, [])

        assert exc_info.value.code == 0
        app._disconnect.assert_called_once()
        mock_del_pw.assert_called_once_with("user")
        mock_del_acct.assert_called_once_with("user")
        mock_ui.print_success.assert_called_once_with("Logged out successfully.")

    def test_logout_with_remaining_accounts_switches(self):
        app = _make_app(account=_TEST_ACCOUNT)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.delete_password") as mock_del_pw,
            patch("cli_mail.commands.account.delete_account") as mock_del_acct,
            patch("cli_mail.commands.account.list_accounts", return_value=["work"]),
        ):
            mock_ui.prompt_confirm.return_value = True
            cmd_account_logout(app, [])

        app._disconnect.assert_called_once()
        mock_del_pw.assert_called_once_with("user")
        mock_del_acct.assert_called_once_with("user")
        mock_ui.print_success.assert_called_once_with("Logged out successfully.")
        app.switch_account.assert_called_once_with("work")
