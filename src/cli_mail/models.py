"""Data models for CLI Mail."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parseaddr


@dataclass
class Address:
    name: str
    email: str

    @classmethod
    def from_header(cls, header: str) -> Address:
        name, email = parseaddr(header)
        return cls(name=name or email.split("@")[0], email=email)

    def __str__(self) -> str:
        if self.name and self.name != self.email:
            return f"{self.name} <{self.email}>"
        return self.email

    @property
    def short(self) -> str:
        return self.name if self.name else self.email.split("@")[0]


@dataclass
class Attachment:
    filename: str
    content_type: str
    size: int
    payload: bytes = field(repr=False)

    @property
    def size_human(self) -> str:
        if self.size < 1024:
            return f"{self.size} B"
        if self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        return f"{self.size / (1024 * 1024):.1f} MB"


@dataclass
class Email:
    uid: str
    message_id: str
    subject: str
    sender: Address
    to: list[Address]
    cc: list[Address]
    date: datetime
    body_plain: str
    body_html: str
    attachments: list[Attachment] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
    in_reply_to: str = ""
    references: str = ""

    @property
    def is_unread(self) -> bool:
        return "\\Seen" not in self.flags

    @property
    def is_flagged(self) -> bool:
        return "\\Flagged" in self.flags

    @property
    def body(self) -> str:
        return self.body_plain or self.body_html


@dataclass
class EmailHeader:
    """Lightweight version of Email for inbox listing — avoids fetching full body."""

    uid: str
    subject: str
    sender: Address
    date: datetime
    flags: set[str] = field(default_factory=set)
    has_attachments: bool = False

    @property
    def is_unread(self) -> bool:
        return "\\Seen" not in self.flags

    @property
    def is_flagged(self) -> bool:
        return "\\Flagged" in self.flags


@dataclass
class Folder:
    name: str
    delimiter: str
    flags: set[str] = field(default_factory=set)
    total: int = 0
    unread: int = 0

    @property
    def display_name(self) -> str:
        parts = self.name.split(self.delimiter) if self.delimiter else [self.name]
        return parts[-1]


@dataclass
class AccountConfig:
    email: str
    imap_host: str
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 587
    use_ssl: bool = True
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.email.split("@")[0]
        if not self.smtp_host and self.imap_host:
            self.smtp_host = self.imap_host.replace("imap", "smtp", 1)


@dataclass
class AppContext:
    """Mutable state for the current session."""

    account: AccountConfig | None = None
    current_folder: str = "INBOX"
    current_page: int = 1
    page_size: int = 20
    current_email: Email | None = None
    inbox_cache: list[EmailHeader] = field(default_factory=list)
    connected: bool = False
