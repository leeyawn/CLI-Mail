"""Tests for SMTP sender — message construction logic (no actual sending)."""

from datetime import datetime, timezone
from email import message_from_string
from unittest.mock import MagicMock, patch

from cli_mail.models import AccountConfig, Address, Email
from cli_mail.sender import SMTPSender


def _make_account(**overrides):
    defaults = dict(
        email="me@example.com",
        imap_host="imap.example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        name="me",
    )
    defaults.update(overrides)
    return AccountConfig(**defaults)


def _make_email(**overrides):
    defaults = dict(
        uid="1",
        message_id="<orig-123@example.com>",
        subject="Original Subject",
        sender=Address(name="Alice", email="alice@example.com"),
        to=[Address(name="me", email="me@example.com")],
        cc=[],
        date=datetime(2026, 2, 20, 10, 30, tzinfo=timezone.utc),
        body_plain="Original body text",
        body_html="",
        references="<ref-001@example.com>",
    )
    defaults.update(overrides)
    return Email(**defaults)


class TestReplySubject:
    def test_adds_re_prefix(self):
        sender = SMTPSender(_make_account())
        original = _make_email(subject="Hello")

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.reply(password="pass", original=original, body="Thanks!")

            sent_msg = mock_server.send_message.call_args[0][0]
            assert sent_msg["Subject"] == "Re: Hello"

    def test_does_not_double_re_prefix(self):
        sender = SMTPSender(_make_account())
        original = _make_email(subject="Re: Hello")

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.reply(password="pass", original=original, body="Thanks!")

            sent_msg = mock_server.send_message.call_args[0][0]
            assert sent_msg["Subject"] == "Re: Hello"

    def test_reply_sets_threading_headers(self):
        sender = SMTPSender(_make_account())
        original = _make_email()

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.reply(password="pass", original=original, body="Reply")

            sent_msg = mock_server.send_message.call_args[0][0]
            assert sent_msg["In-Reply-To"] == "<orig-123@example.com>"
            assert "<ref-001@example.com>" in sent_msg["References"]
            assert "<orig-123@example.com>" in sent_msg["References"]

    def test_reply_to_address(self):
        sender = SMTPSender(_make_account())
        original = _make_email()

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.reply(password="pass", original=original, body="Reply")

            sent_msg = mock_server.send_message.call_args[0][0]
            assert "alice@example.com" in sent_msg["To"]


class TestForwardSubject:
    def test_adds_fwd_prefix(self):
        sender = SMTPSender(_make_account())
        original = _make_email(subject="Meeting Notes")

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.forward(password="pass", original=original, to=["bob@test.com"])

            sent_msg = mock_server.send_message.call_args[0][0]
            assert sent_msg["Subject"] == "Fwd: Meeting Notes"

    def test_does_not_double_fwd_prefix(self):
        sender = SMTPSender(_make_account())
        original = _make_email(subject="Fwd: Meeting Notes")

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.forward(password="pass", original=original, to=["bob@test.com"])

            sent_msg = mock_server.send_message.call_args[0][0]
            assert sent_msg["Subject"] == "Fwd: Meeting Notes"

    def test_forward_includes_original_body(self):
        sender = SMTPSender(_make_account())
        original = _make_email(body_plain="Important content here")

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.forward(password="pass", original=original, to=["bob@test.com"], body="FYI")

            sent_msg = mock_server.send_message.call_args[0][0]
            body = sent_msg.get_content()
            assert "FYI" in body
            assert "Forwarded message" in body
            assert "Important content here" in body


class TestSmtpPortSelection:
    def test_port_465_uses_smtp_ssl(self):
        sender = SMTPSender(_make_account(smtp_port=465))

        with patch("smtplib.SMTP_SSL") as mock_ssl:
            mock_server = MagicMock()
            mock_ssl.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_ssl.return_value.__exit__ = MagicMock(return_value=False)

            sender.send(password="pass", to=["bob@test.com"], subject="Test", body="Hi")

            mock_ssl.assert_called_once_with("smtp.example.com", 465, timeout=30)

    def test_port_587_uses_smtp_starttls(self):
        sender = SMTPSender(_make_account(smtp_port=587))

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.send(password="pass", to=["bob@test.com"], subject="Test", body="Hi")

            mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=30)
            mock_server.starttls.assert_called_once()


class TestSendMessageFields:
    def test_from_and_to_headers(self):
        sender = SMTPSender(_make_account())

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            sender.send(
                password="pass",
                to=["alice@test.com", "bob@test.com"],
                subject="Multi-recipient",
                body="Hello all",
                cc=["charlie@test.com"],
            )

            sent_msg = mock_server.send_message.call_args[0][0]
            assert "me@example.com" in sent_msg["From"]
            assert "alice@test.com" in sent_msg["To"]
            assert "bob@test.com" in sent_msg["To"]
            assert "charlie@test.com" in sent_msg["Cc"]
            assert sent_msg["Subject"] == "Multi-recipient"
