# CLI Mail

A terminal email client with a Claude Code-style interactive interface. Read, compose, search, and manage your email without leaving the terminal.

## Quick Start

```bash
pip install cli-mail
cli-mail
```

On first launch you'll be guided through account setup. CLI Mail auto-detects settings for Gmail, Outlook, Yahoo, iCloud, Fastmail, and ProtonMail (via Bridge).

## Commands

| Command | Aliases | Description |
|---|---|---|
| `/inbox [page]` | `/i`, `/ls` | List emails in current folder |
| `/read <n>` | `/r`, `/open` | Read email #n from the list |
| `/reply` | `/re` | Reply to the currently open email |
| `/compose` | `/c`, `/new` | Compose a new email |
| `/forward <email>` | `/fwd` | Forward the current email |
| `/search <query>` | `/s`, `/find` | Search by subject or sender |
| `/folders` | `/f` | List all mail folders |
| `/switch <folder>` | `/sw`, `/cd` | Switch to a different folder |
| `/star [n]` | `/flag` | Toggle star on an email |
| `/delete [n]` | `/del`, `/rm` | Delete an email |
| `/archive [n]` | `/ar` | Archive an email |
| `/save [n]` | | Save attachment to ~/Downloads |
| `/account` | `/acc` | Show account info |
| `/refresh` | `/ref` | Refresh the inbox |
| `/help` | `/h`, `/?` | Show help |
| `/quit` | `/q`, `/exit` | Exit |

**Shortcuts:** Type a number to read that email. Type text without `/` to search.

## Gmail Setup

Gmail requires an **App Password** (not your regular password):

1. Go to [Google Account → Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication if not already on
3. Go to **App Passwords** → generate one for "Mail"
4. Use that 16-character password when CLI Mail asks

## Configuration

Config is stored at `~/.config/cli-mail/config.toml`. Passwords are stored in your system keychain via `keyring`.

> **Note:** On headless Linux systems, you may need to install a keyring backend such as `keyrings.alt` or have `gnome-keyring` / `SecretService` available. If no backend is found, CLI Mail will prompt for your password each session.

## Development

```bash
git clone https://github.com/leonletournel/cli-mail.git
cd cli-mail
pip install -e ".[dev]"
pytest -v
```

## Requirements

- Python 3.11+
- An email account with IMAP/SMTP access

## License

[MIT](LICENSE)
