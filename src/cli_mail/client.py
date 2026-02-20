"""IMAP client — handles connection, folder operations, and email fetching."""

from __future__ import annotations

import imaplib
import re

from cli_mail.models import AccountConfig, Email, EmailHeader, Folder
from cli_mail.parser import parse_email, parse_header

_LIST_PATTERN = re.compile(
    r'\((?P<flags>[^)]*)\)\s+"(?P<delim>[^"]*)"\s+"?(?P<name>[^"]*)"?'
)
_STATUS_PATTERN = re.compile(r"\(MESSAGES\s+(\d+)\s+UNSEEN\s+(\d+)\)")


class IMAPClient:
    def __init__(self, account: AccountConfig) -> None:
        self.account = account
        self._conn: imaplib.IMAP4_SSL | imaplib.IMAP4 | None = None

    def connect(self, password: str) -> None:
        if self.account.use_ssl:
            self._conn = imaplib.IMAP4_SSL(self.account.imap_host, self.account.imap_port)
        else:
            self._conn = imaplib.IMAP4(self.account.imap_host, self.account.imap_port)
        self._conn.login(self.account.email, password)

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    @property
    def conn(self) -> imaplib.IMAP4_SSL | imaplib.IMAP4:
        if self._conn is None:
            raise ConnectionError("Not connected to IMAP server")
        return self._conn

    def list_folders(self) -> list[Folder]:
        status, data = self.conn.list()
        if status != "OK":
            return []
        folders: list[Folder] = []
        for item in data:
            if item is None:
                continue
            line = item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
            match = _LIST_PATTERN.match(line)
            if not match:
                continue
            flags = {f.strip() for f in match.group("flags").split() if f.strip()}
            name = match.group("name").strip()
            delim = match.group("delim")

            total, unread = 0, 0
            try:
                st, st_data = self.conn.status(f'"{name}"', "(MESSAGES UNSEEN)")
                if st == "OK" and st_data[0]:
                    decoded = st_data[0].decode("utf-8", errors="replace") if isinstance(st_data[0], bytes) else str(st_data[0])
                    sm = _STATUS_PATTERN.search(decoded)
                    if sm:
                        total, unread = int(sm.group(1)), int(sm.group(2))
            except Exception:
                pass

            folders.append(Folder(name=name, delimiter=delim, flags=flags, total=total, unread=unread))
        return folders

    def select_folder(self, folder: str = "INBOX") -> int:
        status, data = self.conn.select(f'"{folder}"')
        if status != "OK":
            raise ValueError(f"Cannot select folder: {folder}")
        return int(data[0])

    def fetch_headers(
        self, folder: str = "INBOX", limit: int = 50, offset: int = 0
    ) -> list[EmailHeader]:
        total = self.select_folder(folder)
        if total == 0:
            return []

        start = max(1, total - offset - limit + 1)
        end = max(1, total - offset)
        if start > end:
            return []

        status, data = self.conn.fetch(f"{start}:{end}", "(UID FLAGS BODY.PEEK[HEADER])")
        if status != "OK":
            return []

        headers: list[EmailHeader] = []
        i = 0
        while i < len(data):
            if isinstance(data[i], tuple) and len(data[i]) >= 2:
                meta_line = data[i][0].decode("utf-8", errors="replace")
                raw_header = data[i][1]

                uid = _extract_uid(meta_line)
                flags = _extract_flags(meta_line)
                headers.append(parse_header(raw_header, uid, flags))
                i += 2
            else:
                i += 1

        headers.reverse()
        return headers

    def fetch_email(self, uid: str, folder: str = "INBOX") -> Email | None:
        self.select_folder(folder)
        status, data = self.conn.uid("fetch", uid, "(FLAGS RFC822)")
        if status != "OK" or not data or data[0] is None:
            return None

        if isinstance(data[0], tuple) and len(data[0]) >= 2:
            meta_line = data[0][0].decode("utf-8", errors="replace")
            raw = data[0][1]
            flags = _extract_flags(meta_line)
            return parse_email(raw, uid, flags)

        return None

    def search(self, query: str, folder: str = "INBOX") -> list[EmailHeader]:
        self.select_folder(folder)

        sanitized = query.replace("\\", "\\\\").replace('"', '\\"')
        criteria = f'(OR (SUBJECT "{sanitized}") (FROM "{sanitized}"))'
        status, data = self.conn.search(None, criteria)
        if status != "OK" or not data[0]:
            return []

        msg_nums = data[0].split()[-50:]
        if not msg_nums:
            return []

        num_range = b",".join(msg_nums)
        status, data = self.conn.fetch(num_range.decode(), "(UID FLAGS BODY.PEEK[HEADER])")
        if status != "OK":
            return []

        headers: list[EmailHeader] = []
        i = 0
        while i < len(data):
            if isinstance(data[i], tuple) and len(data[i]) >= 2:
                meta_line = data[i][0].decode("utf-8", errors="replace")
                raw_header = data[i][1]
                uid = _extract_uid(meta_line)
                flags = _extract_flags(meta_line)
                headers.append(parse_header(raw_header, uid, flags))
                i += 2
            else:
                i += 1

        headers.reverse()
        return headers

    def set_flag(self, uid: str, flag: str, folder: str = "INBOX") -> bool:
        self.select_folder(folder)
        status, _ = self.conn.uid("store", uid, "+FLAGS", flag)
        return status == "OK"

    def remove_flag(self, uid: str, flag: str, folder: str = "INBOX") -> bool:
        self.select_folder(folder)
        status, _ = self.conn.uid("store", uid, "-FLAGS", flag)
        return status == "OK"

    def delete_email(self, uid: str, folder: str = "INBOX") -> bool:
        if not self.set_flag(uid, "\\Deleted", folder):
            return False
        self.conn.expunge()
        return True

    def move_email(self, uid: str, dest_folder: str, src_folder: str = "INBOX") -> bool:
        self.select_folder(src_folder)
        try:
            status, _ = self.conn.uid("copy", uid, dest_folder)
            if status == "OK":
                self.set_flag(uid, "\\Deleted", src_folder)
                self.conn.expunge()
                return True
        except Exception:
            pass
        return False

    def folder_status(self, folder: str = "INBOX") -> tuple[int, int]:
        status, data = self.conn.status(f'"{folder}"', "(MESSAGES UNSEEN)")
        if status == "OK" and data[0]:
            decoded = data[0].decode("utf-8", errors="replace") if isinstance(data[0], bytes) else str(data[0])
            match = _STATUS_PATTERN.search(decoded)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 0, 0


def _extract_uid(meta: str) -> str:
    match = re.search(r"UID\s+(\d+)", meta)
    return match.group(1) if match else "0"


def _extract_flags(meta: str) -> set[str]:
    match = re.search(r"FLAGS\s+\(([^)]*)\)", meta)
    if not match:
        return set()
    return {f.strip() for f in match.group(1).split() if f.strip()}
