"""SMTP client — handles sending, replying to, and forwarding emails."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate

from cli_mail.models import AccountConfig, Email


class SMTPSender:
    def __init__(self, account: AccountConfig) -> None:
        self.account = account

    def send(
        self,
        password: str,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        in_reply_to: str = "",
        references: str = "",
    ) -> None:
        msg = EmailMessage()
        msg["From"] = formataddr((self.account.name, self.account.email))
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        msg.set_content(body)

        timeout = 30
        if self.account.smtp_port == 465:
            with smtplib.SMTP_SSL(self.account.smtp_host, self.account.smtp_port, timeout=timeout) as server:
                server.login(self.account.email, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.account.smtp_host, self.account.smtp_port, timeout=timeout) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.account.email, password)
                server.send_message(msg)

    def reply(self, password: str, original: Email, body: str) -> None:
        subject = original.subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        refs = original.references
        if original.message_id:
            refs = f"{refs} {original.message_id}".strip()

        self.send(
            password=password,
            to=[str(original.sender)],
            subject=subject,
            body=body,
            in_reply_to=original.message_id,
            references=refs,
        )

    def forward(self, password: str, original: Email, to: list[str], body: str = "") -> None:
        subject = original.subject
        if not subject.lower().startswith("fwd:"):
            subject = f"Fwd: {subject}"

        fwd_body = body
        fwd_body += "\n\n---------- Forwarded message ----------\n"
        fwd_body += f"From: {original.sender}\n"
        fwd_body += f"Date: {original.date.strftime('%a, %b %d, %Y at %I:%M %p')}\n"
        fwd_body += f"Subject: {original.subject}\n"
        fwd_body += f"To: {', '.join(str(a) for a in original.to)}\n\n"
        fwd_body += original.body

        self.send(password=password, to=to, subject=subject, body=fwd_body)
