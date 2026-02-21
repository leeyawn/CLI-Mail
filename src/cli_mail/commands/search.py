"""Search command — find emails by subject or sender."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cli_mail import ui

if TYPE_CHECKING:
    from cli_mail.app import App


def cmd_search(app: App, args: list[str]) -> None:
    if app.imap is None:
        ui.print_error("Not connected.")
        return
    if not args:
        ui.print_error("Usage: /search <query>")
        return

    query = " ".join(args)
    app.ctx.current_email = None

    with ui.console.status(f'[info]Searching for "{query}"...[/info]', spinner="dots"):
        results = app.imap.search(query, folder=app.ctx.current_folder)

    if not results:
        ui.print_warning(f'No results for "{query}"')
        return

    # Reuse inbox_cache so /read <n> works on search results too
    app.ctx.inbox_cache = results
    ui.print_info(f'Found {len(results)} result{"s" if len(results) != 1 else ""} for "{query}"')
    ui.print_inbox(results, page=1, total_pages=1)
