"""Tests for /account subcommands: switch, default, add, list, and dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cli_mail.commands.account import (cmd_account_add, cmd_account_default,
                                       cmd_account_dispatch, cmd_account_list,
                                       cmd_account_switch)
from cli_mail.models import AccountConfig, AppContext


def _make_app(account: AccountConfig | None = None) -> MagicMock:
    app = MagicMock()
    app.ctx = AppContext(account=account, connected=account is not None)
    app._passwords = {}
    return app


_ACCT_WORK = AccountConfig(email="me@work.com", imap_host="imap.work.com", name="work")
_ACCT_PERSONAL = AccountConfig(email="me@gmail.com", imap_host="imap.gmail.com", name="personal")


class TestCmdAccountSwitch:
    def test_no_accounts_warns(self):
        app = _make_app()

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.list_accounts", return_value=[]),
        ):
            cmd_account_switch(app, [])

        mock_ui.print_warning.assert_called_once_with("No accounts configured.")

    def test_single_account_skips_switch_prompt(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.list_accounts", return_value=["work"]),
            patch("cli_mail.commands.account.get_account", return_value=_ACCT_WORK),
            patch("cli_mail.commands.account.get_default_account_name", return_value="work"),
        ):
            cmd_account_switch(app, [])

        mock_ui.prompt_input.assert_not_called()
        app.switch_account.assert_not_called()

    def test_switch_by_number(self):
        app = _make_app(account=_ACCT_WORK)

        def fake_get_account(name):
            return {"work": _ACCT_WORK, "personal": _ACCT_PERSONAL}.get(name)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.list_accounts", return_value=["work", "personal"]),
            patch("cli_mail.commands.account.get_account", side_effect=fake_get_account),
            patch("cli_mail.commands.account.get_default_account_name", return_value="work"),
        ):
            mock_ui.prompt_input.return_value = "2"
            cmd_account_switch(app, [])

        app.switch_account.assert_called_once_with("personal")

    def test_switch_by_name_arg(self):
        app = _make_app(account=_ACCT_WORK)

        with patch("cli_mail.commands.account.ui"):
            cmd_account_switch(app, ["personal"])

        app.switch_account.assert_called_once_with("personal")

    def test_switch_cancel_on_empty_input(self):
        app = _make_app(account=_ACCT_WORK)

        def fake_get_account(name):
            return {"work": _ACCT_WORK, "personal": _ACCT_PERSONAL}.get(name)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.list_accounts", return_value=["work", "personal"]),
            patch("cli_mail.commands.account.get_account", side_effect=fake_get_account),
            patch("cli_mail.commands.account.get_default_account_name", return_value="work"),
        ):
            mock_ui.prompt_input.return_value = ""
            cmd_account_switch(app, [])

        app.switch_account.assert_not_called()

    def test_switch_to_already_active_shows_info(self):
        app = _make_app(account=_ACCT_WORK)

        def fake_get_account(name):
            return {"work": _ACCT_WORK, "personal": _ACCT_PERSONAL}.get(name)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.list_accounts", return_value=["work", "personal"]),
            patch("cli_mail.commands.account.get_account", side_effect=fake_get_account),
            patch("cli_mail.commands.account.get_default_account_name", return_value="work"),
        ):
            mock_ui.prompt_input.return_value = "1"
            cmd_account_switch(app, [])

        app.switch_account.assert_not_called()
        mock_ui.print_info.assert_called_once_with("Already on work.")

    def test_switch_to_already_active_by_name_arg(self):
        app = _make_app(account=_ACCT_WORK)

        with patch("cli_mail.commands.account.ui") as mock_ui:
            cmd_account_switch(app, ["work"])

        app.switch_account.assert_not_called()
        mock_ui.print_info.assert_called_once_with("Already on work.")

    def test_invalid_number_shows_error(self):
        app = _make_app(account=_ACCT_WORK)

        def fake_get_account(name):
            return {"work": _ACCT_WORK, "personal": _ACCT_PERSONAL}.get(name)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.list_accounts", return_value=["work", "personal"]),
            patch("cli_mail.commands.account.get_account", side_effect=fake_get_account),
            patch("cli_mail.commands.account.get_default_account_name", return_value="work"),
        ):
            mock_ui.prompt_input.return_value = "99"
            cmd_account_switch(app, [])

        app.switch_account.assert_not_called()
        mock_ui.print_error.assert_called_once_with("Invalid selection.")


class TestCmdAccountList:
    def test_no_accounts_warns(self):
        app = _make_app()

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.list_accounts", return_value=[]),
        ):
            cmd_account_list(app, [])

        mock_ui.print_warning.assert_called_once_with("No accounts configured.")

    def test_lists_accounts(self):
        app = _make_app(account=_ACCT_WORK)

        def fake_get_account(name):
            return {"work": _ACCT_WORK, "personal": _ACCT_PERSONAL}.get(name)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.list_accounts", return_value=["work", "personal"]),
            patch("cli_mail.commands.account.get_account", side_effect=fake_get_account),
            patch("cli_mail.commands.account.get_default_account_name", return_value="work"),
        ):
            cmd_account_list(app, [])

        mock_ui.print_accounts.assert_called_once()


class TestCmdAccountDefault:
    def test_no_args_shows_usage(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.get_default_account_name", return_value="work"),
        ):
            cmd_account_default(app, [])

        assert any("Current default: work" in str(c) for c in mock_ui.print_info.call_args_list)

    def test_set_valid_account(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.set_default_account", return_value=True),
        ):
            cmd_account_default(app, ["personal"])

        mock_ui.print_success.assert_called_once_with("Default account set to personal.")

    def test_set_nonexistent_account(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.ui") as mock_ui,
            patch("cli_mail.commands.account.set_default_account", return_value=False),
            patch("cli_mail.commands.account.list_accounts", return_value=["work"]),
        ):
            cmd_account_default(app, ["nope"])

        mock_ui.print_error.assert_called_once_with('Account "nope" not found.')


class TestCmdAccountAdd:
    def test_add_and_switch(self):
        app = _make_app(account=_ACCT_WORK)
        app.setup_new_account.return_value = _ACCT_PERSONAL

        with patch("cli_mail.commands.account.ui") as mock_ui:
            mock_ui.prompt_confirm.return_value = True
            cmd_account_add(app, [])

        app.setup_new_account.assert_called_once()
        app.switch_account.assert_called_once_with("personal")

    def test_add_without_switch(self):
        app = _make_app(account=_ACCT_WORK)
        app.setup_new_account.return_value = _ACCT_PERSONAL

        with patch("cli_mail.commands.account.ui") as mock_ui:
            mock_ui.prompt_confirm.return_value = False
            cmd_account_add(app, [])

        app.setup_new_account.assert_called_once()
        app.switch_account.assert_not_called()

    def test_add_cancelled(self):
        app = _make_app(account=_ACCT_WORK)
        app.setup_new_account.return_value = None

        with patch("cli_mail.commands.account.ui"):
            cmd_account_add(app, [])

        app.switch_account.assert_not_called()


class TestCmdAccountDispatch:
    def test_no_args_shows_info(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.ui"),
            patch("cli_mail.commands.account.get_default_account_name", return_value="work"),
            patch("cli_mail.commands.account.list_accounts", return_value=["work"]),
        ):
            cmd_account_dispatch(app, [])

    def test_routes_to_list(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.cmd_account_list") as mock_list,
        ):
            cmd_account_dispatch(app, ["list"])

        mock_list.assert_called_once_with(app, [])

    def test_routes_to_switch(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.cmd_account_switch") as mock_switch,
        ):
            cmd_account_dispatch(app, ["switch", "personal"])

        mock_switch.assert_called_once_with(app, ["personal"])

    def test_routes_to_add(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.cmd_account_add") as mock_add,
        ):
            cmd_account_dispatch(app, ["add"])

        mock_add.assert_called_once_with(app, [])

    def test_routes_to_default(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.cmd_account_default") as mock_default,
        ):
            cmd_account_dispatch(app, ["default", "work"])

        mock_default.assert_called_once_with(app, ["work"])

    def test_routes_to_logout(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.cmd_account_logout") as mock_logout,
        ):
            cmd_account_dispatch(app, ["logout"])

        mock_logout.assert_called_once_with(app, [])

    def test_unknown_subcommand_shows_error(self):
        app = _make_app(account=_ACCT_WORK)

        with patch("cli_mail.commands.account.ui") as mock_ui:
            cmd_account_dispatch(app, ["bogus"])

        mock_ui.print_error.assert_called_once_with("Unknown subcommand: bogus")

    def test_subcommand_is_case_insensitive(self):
        app = _make_app(account=_ACCT_WORK)

        with (
            patch("cli_mail.commands.account.cmd_account_list") as mock_list,
        ):
            cmd_account_dispatch(app, ["LIST"])

        mock_list.assert_called_once_with(app, [])
