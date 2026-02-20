"""Parse raw MIME email messages into our Email model."""

from __future__ import annotations

import email
import email.policy
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parsedate_to_datetime

import html2text

from cli_mail.models import Address, Attachment, Email, EmailHeader

_h2t = html2text.HTML2Text()
_h2t.body_width = 80
_h2t.ignore_images = False
_h2t.ignore_links = False
_h2t.protect_links = True
_h2t.unicode_snob = True


def html_to_text(html: str) -> str:
    return _h2t.handle(html).strip()


def _parse_address_list(header: str | None) -> list[Address]:
    if not header:
        return []
    parts = header.split(",")
    return [Address.from_header(p.strip()) for p in parts if p.strip()]


def _parse_date(msg: EmailMessage) -> datetime:
    date_str = msg.get("Date", "")
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return datetime.now(timezone.utc)


def _extract_body(msg: EmailMessage) -> tuple[str, str]:
    """Return (plain_text, html_text) from a message."""
    plain = ""
    html = ""

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            if ct == "text/plain" and not plain:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    plain = payload.decode(charset, errors="replace")
            elif ct == "text/html" and not html:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    html = payload.decode(charset, errors="replace")
    else:
        ct = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if ct == "text/html":
                html = text
            else:
                plain = text

    if html and not plain:
        plain = html_to_text(html)

    return plain, html


def _extract_attachments(msg: EmailMessage) -> list[Attachment]:
    attachments: list[Attachment] = []
    if not msg.is_multipart():
        return attachments

    for part in msg.walk():
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" not in disposition and "inline" not in disposition:
            continue
        ct = part.get_content_type()
        if ct in ("text/plain", "text/html") and "attachment" not in disposition:
            continue

        filename = part.get_filename() or "unnamed"
        raw_payload = part.get_payload(decode=True)
        payload = raw_payload if isinstance(raw_payload, bytes) else b""
        attachments.append(
            Attachment(
                filename=filename,
                content_type=ct,
                size=len(payload),
                payload=payload,
            )
        )

    return attachments


def parse_email(raw: bytes, uid: str, flags: set[str] | None = None) -> Email:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    plain, html_body = _extract_body(msg)
    attachments = _extract_attachments(msg)

    return Email(
        uid=uid,
        message_id=msg.get("Message-ID", ""),
        subject=msg.get("Subject", "(no subject)"),
        sender=Address.from_header(msg.get("From", "")),
        to=_parse_address_list(msg.get("To")),
        cc=_parse_address_list(msg.get("Cc")),
        date=_parse_date(msg),
        body_plain=plain,
        body_html=html_body,
        attachments=attachments,
        flags=flags or set(),
        in_reply_to=msg.get("In-Reply-To", ""),
        references=msg.get("References", ""),
    )


def parse_header(raw: bytes, uid: str, flags: set[str] | None = None) -> EmailHeader:
    msg = email.message_from_bytes(raw, policy=email.policy.default)

    has_attachments = False
    if msg.is_multipart():
        for part in msg.walk():
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                has_attachments = True
                break

    return EmailHeader(
        uid=uid,
        subject=msg.get("Subject", "(no subject)"),
        sender=Address.from_header(msg.get("From", "")),
        date=_parse_date(msg),
        flags=flags or set(),
        has_attachments=has_attachments,
    )
