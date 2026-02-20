"""Tests for email parsing."""

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from cli_mail.parser import html_to_text, parse_email, parse_header


def _build_plain_email(
    subject="Test Subject",
    from_addr="Alice <alice@example.com>",
    to_addr="bob@example.com",
    body="Hello, world!",
    date="Thu, 20 Feb 2026 10:30:00 +0000",
) -> bytes:
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Date"] = date
    msg["Message-ID"] = "<test-123@example.com>"
    return msg.as_bytes()


def _build_html_email(html_body="<h1>Hello</h1><p>World</p>") -> bytes:
    msg = MIMEText(html_body, "html")
    msg["Subject"] = "HTML Email"
    msg["From"] = "sender@example.com"
    msg["To"] = "recipient@example.com"
    msg["Date"] = "Thu, 20 Feb 2026 10:30:00 +0000"
    return msg.as_bytes()


def _build_multipart_email(
    plain_body="Plain text",
    html_body="<p>HTML text</p>",
    attachments=None,
) -> bytes:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = "Multipart Email"
    msg["From"] = "Alice <alice@example.com>"
    msg["To"] = "bob@example.com, charlie@example.com"
    msg["Cc"] = "dave@example.com"
    msg["Date"] = "Thu, 20 Feb 2026 10:30:00 +0000"
    msg["Message-ID"] = "<multi-456@example.com>"
    msg["In-Reply-To"] = "<original-789@example.com>"

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_body, "plain"))
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    for att_name, att_data in (attachments or []):
        part = MIMEBase("application", "octet-stream")
        part.set_payload(att_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={att_name}")
        msg.attach(part)

    return msg.as_bytes()


class TestHtmlToText:
    def test_simple_paragraph(self):
        result = html_to_text("<p>Hello world</p>")
        assert "Hello world" in result

    def test_heading(self):
        result = html_to_text("<h1>Title</h1>")
        assert "Title" in result

    def test_link_preserved(self):
        result = html_to_text('<a href="https://example.com">Click here</a>')
        assert "example.com" in result

    def test_empty_html(self):
        result = html_to_text("")
        assert result == ""


class TestParseEmail:
    def test_plain_text_email(self):
        raw = _build_plain_email()
        email = parse_email(raw, uid="42")

        assert email.uid == "42"
        assert email.subject == "Test Subject"
        assert email.sender.name == "Alice"
        assert email.sender.email == "alice@example.com"
        assert email.body_plain == "Hello, world!"
        assert email.message_id == "<test-123@example.com>"
        assert len(email.to) == 1
        assert email.to[0].email == "bob@example.com"

    def test_html_only_email(self):
        raw = _build_html_email("<p>Only HTML</p>")
        email = parse_email(raw, uid="1")

        assert email.body_html == "<p>Only HTML</p>"
        assert "Only HTML" in email.body_plain

    def test_multipart_email(self):
        raw = _build_multipart_email()
        email = parse_email(raw, uid="10")

        assert email.subject == "Multipart Email"
        assert email.body_plain == "Plain text"
        assert "<p>HTML text</p>" in email.body_html
        assert len(email.to) == 2
        assert len(email.cc) == 1
        assert email.cc[0].email == "dave@example.com"
        assert email.in_reply_to == "<original-789@example.com>"

    def test_multipart_with_attachment(self):
        raw = _build_multipart_email(
            attachments=[("report.pdf", b"fake-pdf-content")]
        )
        email = parse_email(raw, uid="20")

        assert len(email.attachments) == 1
        assert email.attachments[0].filename == "report.pdf"
        assert email.attachments[0].size == len(b"fake-pdf-content")

    def test_multiple_attachments(self):
        raw = _build_multipart_email(
            attachments=[
                ("file1.txt", b"content1"),
                ("file2.zip", b"content2content2"),
            ]
        )
        email = parse_email(raw, uid="30")

        assert len(email.attachments) == 2
        filenames = {a.filename for a in email.attachments}
        assert filenames == {"file1.txt", "file2.zip"}

    def test_flags_passed_through(self):
        raw = _build_plain_email()
        email = parse_email(raw, uid="1", flags={"\\Seen", "\\Flagged"})

        assert email.is_unread is False
        assert email.is_flagged is True

    def test_no_subject(self):
        msg = MIMEText("body")
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        raw = msg.as_bytes()

        email = parse_email(raw, uid="1")
        assert email.subject == "(no subject)"

    def test_date_parsing(self):
        raw = _build_plain_email(date="Thu, 20 Feb 2026 10:30:00 +0000")
        email = parse_email(raw, uid="1")

        assert email.date.year == 2026
        assert email.date.month == 2
        assert email.date.day == 20


class TestParseHeader:
    def test_basic_header(self):
        raw = _build_plain_email(subject="Important", from_addr="Bob <bob@test.com>")
        header = parse_header(raw, uid="99")

        assert header.uid == "99"
        assert header.subject == "Important"
        assert header.sender.name == "Bob"
        assert header.sender.email == "bob@test.com"

    def test_header_flags(self):
        raw = _build_plain_email()
        header = parse_header(raw, uid="1", flags={"\\Seen"})

        assert header.is_unread is False

    def test_has_attachments_false_for_plain(self):
        raw = _build_plain_email()
        header = parse_header(raw, uid="1")

        assert header.has_attachments is False

    def test_has_attachments_true(self):
        raw = _build_multipart_email(attachments=[("file.pdf", b"data")])
        header = parse_header(raw, uid="1")

        assert header.has_attachments is True
