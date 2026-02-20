"""Tests for data models."""

from datetime import datetime, timezone

from cli_mail.models import (
    AccountConfig,
    Address,
    AppContext,
    Attachment,
    Email,
    EmailHeader,
    Folder,
)


class TestAddress:
    def test_from_header_with_name(self):
        addr = Address.from_header("Alice Smith <alice@example.com>")
        assert addr.name == "Alice Smith"
        assert addr.email == "alice@example.com"

    def test_from_header_email_only(self):
        addr = Address.from_header("bob@example.com")
        assert addr.name == "bob"
        assert addr.email == "bob@example.com"

    def test_from_header_empty(self):
        addr = Address.from_header("")
        assert addr.email == ""

    def test_str_with_name(self):
        addr = Address(name="Alice", email="alice@example.com")
        assert str(addr) == "Alice <alice@example.com>"

    def test_str_email_only(self):
        addr = Address(name="alice@example.com", email="alice@example.com")
        assert str(addr) == "alice@example.com"

    def test_short_with_name(self):
        addr = Address(name="Alice Smith", email="alice@example.com")
        assert addr.short == "Alice Smith"

    def test_short_without_name(self):
        addr = Address(name="", email="alice@example.com")
        assert addr.short == "alice"


class TestAttachment:
    def test_size_bytes(self):
        att = Attachment(filename="f.txt", content_type="text/plain", size=500, payload=b"x")
        assert att.size_human == "500 B"

    def test_size_kilobytes(self):
        att = Attachment(filename="f.txt", content_type="text/plain", size=2048, payload=b"x")
        assert att.size_human == "2.0 KB"

    def test_size_megabytes(self):
        att = Attachment(filename="f.pdf", content_type="application/pdf", size=3_500_000, payload=b"x")
        assert att.size_human == "3.3 MB"


class TestEmail:
    def _make_email(self, flags=None):
        return Email(
            uid="1",
            message_id="<msg@example.com>",
            subject="Test",
            sender=Address(name="Alice", email="alice@example.com"),
            to=[Address(name="Bob", email="bob@example.com")],
            cc=[],
            date=datetime(2026, 2, 20, tzinfo=timezone.utc),
            body_plain="Hello",
            body_html="<p>Hello</p>",
            flags=flags or set(),
        )

    def test_is_unread_when_no_seen_flag(self):
        email = self._make_email()
        assert email.is_unread is True

    def test_is_read_when_seen_flag(self):
        email = self._make_email(flags={"\\Seen"})
        assert email.is_unread is False

    def test_is_flagged(self):
        email = self._make_email(flags={"\\Flagged"})
        assert email.is_flagged is True

    def test_is_not_flagged(self):
        email = self._make_email()
        assert email.is_flagged is False

    def test_body_prefers_plain(self):
        email = self._make_email()
        assert email.body == "Hello"

    def test_body_falls_back_to_html(self):
        email = self._make_email()
        email.body_plain = ""
        assert email.body == "<p>Hello</p>"


class TestEmailHeader:
    def test_is_unread(self):
        h = EmailHeader(
            uid="1",
            subject="Test",
            sender=Address(name="Alice", email="alice@example.com"),
            date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert h.is_unread is True

    def test_is_read(self):
        h = EmailHeader(
            uid="1",
            subject="Test",
            sender=Address(name="Alice", email="alice@example.com"),
            date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            flags={"\\Seen"},
        )
        assert h.is_unread is False


class TestFolder:
    def test_display_name_with_delimiter(self):
        f = Folder(name="INBOX/Subfolder/Deep", delimiter="/")
        assert f.display_name == "Deep"

    def test_display_name_dot_delimiter(self):
        f = Folder(name="INBOX.Drafts", delimiter=".")
        assert f.display_name == "Drafts"

    def test_display_name_no_delimiter(self):
        f = Folder(name="INBOX", delimiter="")
        assert f.display_name == "INBOX"


class TestAccountConfig:
    def test_name_defaults_to_email_prefix(self):
        acct = AccountConfig(email="user@example.com", imap_host="imap.example.com")
        assert acct.name == "user"

    def test_smtp_host_inferred_from_imap(self):
        acct = AccountConfig(email="user@example.com", imap_host="imap.example.com")
        assert acct.smtp_host == "smtp.example.com"

    def test_explicit_name_preserved(self):
        acct = AccountConfig(email="user@example.com", imap_host="imap.example.com", name="work")
        assert acct.name == "work"

    def test_explicit_smtp_host_preserved(self):
        acct = AccountConfig(
            email="user@example.com",
            imap_host="imap.example.com",
            smtp_host="mail.example.com",
        )
        assert acct.smtp_host == "mail.example.com"

    def test_default_ports(self):
        acct = AccountConfig(email="user@example.com", imap_host="imap.example.com")
        assert acct.imap_port == 993
        assert acct.smtp_port == 587


class TestAppContext:
    def test_defaults(self):
        ctx = AppContext()
        assert ctx.current_folder == "INBOX"
        assert ctx.current_page == 1
        assert ctx.page_size == 20
        assert ctx.connected is False
        assert ctx.current_email is None
        assert ctx.inbox_cache == []
