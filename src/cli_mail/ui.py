"""Rich-based terminal UI rendering — the visual layer of CLI Mail."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from cli_mail import __version__
from cli_mail.models import AppContext, Email, EmailHeader, Folder

THEME = Theme(
    {
        "header": "bold cyan",
        "unread": "bold white",
        "read": "dim white",
        "flagged": "bold yellow",
        "folder": "bold magenta",
        "date": "green",
        "sender": "bold blue",
        "attachment": "yellow",
        "success": "bold green",
        "error": "bold red",
        "warn": "bold yellow",
        "info": "bold cyan",
        "muted": "dim",
    }
)

console = Console(theme=THEME)


def print_banner() -> None:
    banner = Text()
    banner.append("  CLI Mail", style="bold cyan")
    banner.append(f" v{__version__}", style="dim")
    banner.append("  —  ", style="dim")
    banner.append("Your terminal email client", style="dim italic")
    console.print()
    console.print(Panel(banner, border_style="cyan", padding=(0, 1)))
    console.print()


def print_status_bar(ctx: AppContext) -> None:
    parts: list[str] = []
    if ctx.account:
        parts.append(f"[sender]{ctx.account.email}[/sender]")
    parts.append(f"[folder]{ctx.current_folder}[/folder]")
    if ctx.connected:
        parts.append("[success]●[/success] connected")
    else:
        parts.append("[error]○[/error] disconnected")
    console.print("  ".join(parts))
    console.print()


def print_inbox(headers: list[EmailHeader], page: int, total_pages: int) -> None:
    if not headers:
        console.print("  [muted]No messages in this folder.[/muted]")
        return

    table = Table(
        show_header=True,
        header_style="bold",
        border_style="dim",
        padding=(0, 1),
        expand=True,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("", width=2)
    table.add_column("From", style="sender", min_width=18, max_width=24, no_wrap=True)
    table.add_column("Subject", min_width=20, ratio=1)
    table.add_column("Date", style="date", width=16, justify="right", no_wrap=True)

    for i, h in enumerate(headers, start=1):
        idx = str(i)
        status_parts: list[str] = []
        if h.is_unread:
            status_parts.append("[unread]●[/unread]")
        if h.is_flagged:
            status_parts.append("[flagged]★[/flagged]")
        if h.has_attachments:
            status_parts.append("[attachment]📎[/attachment]")
        status = " ".join(status_parts)

        style = "unread" if h.is_unread else "read"
        subject = Text(h.subject or "(no subject)", style=style, overflow="ellipsis", no_wrap=True)
        sender = Text(h.sender.short, overflow="ellipsis", no_wrap=True)
        date_str = _format_date_short(h.date)

        table.add_row(idx, status, sender, subject, date_str)

    console.print(table)

    if total_pages > 1:
        nav = f"  [muted]Page {page}/{total_pages}[/muted]"
        if page < total_pages:
            nav += f"  [muted]— type[/muted] /inbox {page + 1} [muted]for next page[/muted]"
        elif page > 1:
            nav += f"  [muted]— type[/muted] /inbox {page - 1} [muted]for previous page[/muted]"
        console.print(nav)
    console.print()


def print_email(email: Email) -> None:
    header_table = Table.grid(padding=(0, 2))
    header_table.add_column(style="bold", width=10, justify="right")
    header_table.add_column()

    header_table.add_row("From", f"[sender]{email.sender}[/sender]")
    header_table.add_row("To", ", ".join(str(a) for a in email.to))
    if email.cc:
        header_table.add_row("Cc", ", ".join(str(a) for a in email.cc))
    header_table.add_row("Date", f"[date]{email.date.strftime('%a, %b %d, %Y at %I:%M %p')}[/date]")

    body = email.body_plain or "(empty)"

    parts = [header_table, Rule(style="dim")]

    # Render as Markdown when the source is HTML (already converted to text
    # by html2text which outputs Markdown), plain text otherwise.
    if email.body_html and not email.body_plain:
        parts.append(Markdown(body))
    else:
        parts.append(Text(body))

    if email.attachments:
        parts.append(Rule(style="dim"))
        att_lines = Text()
        att_lines.append("📎 Attachments:\n", style="attachment")
        for att in email.attachments:
            att_lines.append(f"   • {att.filename}", style="bold")
            att_lines.append(f" ({att.size_human})\n", style="muted")
        parts.append(att_lines)

    title = email.subject or "(no subject)"
    flags_display = ""
    if email.is_flagged:
        flags_display = " ★"

    console.print()
    console.print(
        Panel(
            Group(*parts),  # type: ignore[arg-type]
            title=f"[bold]{title}[/bold]{flags_display}",
            title_align="left",
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()


def print_folders(folders: list[Folder], current: str) -> None:
    table = Table(
        show_header=True,
        header_style="bold",
        border_style="dim",
        padding=(0, 1),
    )
    table.add_column("", width=2)
    table.add_column("Folder", style="folder")
    table.add_column("Total", justify="right", width=8)
    table.add_column("Unread", justify="right", width=8)

    for f in folders:
        marker = "[success]▸[/success]" if f.name == current else " "
        unread_style = "bold yellow" if f.unread > 0 else "dim"
        table.add_row(
            marker,
            f.display_name,
            str(f.total),
            Text(str(f.unread), style=unread_style),
        )

    console.print(table)
    console.print()


def print_help() -> None:
    help_table = Table(
        show_header=False,
        border_style="dim",
        padding=(0, 2),
        expand=True,
    )
    help_table.add_column("Command", style="bold cyan", min_width=24, no_wrap=True)
    help_table.add_column("Description")

    commands = [
        ("/inbox [page]", "List emails in current folder"),
        ("/read <n>", "Read email #n from the inbox list"),
        ("/reply", "Reply to the currently open email"),
        ("/compose", "Compose a new email"),
        ("/forward <email>", "Forward the current email"),
        ("/search <query>", "Search emails by subject or sender"),
        ("/folders", "List all mail folders"),
        ("/switch <folder>", "Switch to a different folder"),
        ("/star [n]", "Toggle star on email #n or current"),
        ("/delete [n]", "Delete email #n or current"),
        ("/archive [n]", "Archive email #n or current"),
        ("/account", "Show current account info"),
        ("/refresh", "Refresh the inbox"),
        ("/help", "Show this help message"),
        ("/quit", "Exit CLI Mail"),
    ]

    for cmd, desc in commands:
        help_table.add_row(cmd, desc)

    console.print(Panel(help_table, title="[bold]Commands[/bold]", title_align="left", border_style="cyan"))
    console.print()


def print_compose_help() -> None:
    console.print("  [info]Compose mode[/info] — enter your message, then:")
    console.print("  [muted]  Type[/muted] :send [muted]on a new line to send[/muted]")
    console.print("  [muted]  Type[/muted] :cancel [muted]on a new line to discard[/muted]")
    console.print()


def print_success(message: str) -> None:
    console.print(f"  [success]✓[/success] {message}")


def print_error(message: str) -> None:
    console.print(f"  [error]✗[/error] {message}")


def print_warning(message: str) -> None:
    console.print(f"  [warn]![/warn] {message}")


def print_info(message: str) -> None:
    console.print(f"  [info]ℹ[/info] {message}")


def _format_date_short(dt: datetime) -> str:
    """Format a date progressively: today shows time, recent shows day name,
    same year shows month/day, older shows full date. Mirrors Gmail's style."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt

    if diff.days == 0:
        return dt.strftime("%I:%M %p")
    if diff.days == 1:
        return "Yesterday"
    if diff.days < 7:
        return dt.strftime("%a")
    if dt.year == now.year:
        return dt.strftime("%b %d")
    return dt.strftime("%b %d, %Y")


def prompt_input(label: str, default: str = "") -> str:
    """Simple rich-styled input prompt (used during setup, not the main REPL)."""
    suffix = f" [{default}]" if default else ""
    try:
        value = console.input(f"  [bold]{label}[/bold]{suffix}: ")
        return value.strip() or default
    except (EOFError, KeyboardInterrupt):
        return default


def prompt_password(label: str = "Password") -> str:
    import getpass
    try:
        return getpass.getpass(f"  {label}: ")
    except (EOFError, KeyboardInterrupt):
        return ""


def prompt_confirm(label: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        value = console.input(f"  [bold]{label}[/bold] [{hint}]: ").strip().lower()
        if not value:
            return default
        return value in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return default
