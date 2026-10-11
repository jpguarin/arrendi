"""Sending email. The only module that talks to the provider.

It also holds the one rule that keeps test emails away from real tenants: see
`build_sender`.
"""

import base64
import re
from dataclasses import dataclass, field, replace
from typing import Protocol

import httpx2

from app.config import Settings

RESEND_URL = "https://api.resend.com/emails"
TIMEOUT_SECONDS = 15


class EmailError(Exception):
    """The email did not go out."""


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    content_type: str


@dataclass(frozen=True)
class EmailMessage:
    to: str
    # Shown as the sender; the address is always Arrendi's.
    sender_name: str
    # Where the tenant's answer goes: the owner.
    reply_to: str
    subject: str
    html: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)
    bcc: str | None = None
    # The same key twice sends one email, so a retry cannot repeat it.
    idempotency_key: str | None = None


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> str:
        """Sends the email and returns the provider's id for it."""


def _display_name(name: str) -> str:
    """The owner's name as part of a `From` header: nothing that could break out of it."""
    return re.sub(r'[<>"\\\r\n,;]+', " ", name).strip()


class ResendSender:
    def __init__(
        self, api_key: str, sender_address: str, transport: httpx2.BaseTransport | None = None
    ) -> None:
        self.sender_address = sender_address
        self.client = httpx2.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT_SECONDS,
            transport=transport,
        )

    def send(self, message: EmailMessage) -> str:
        body: dict[str, object] = {
            "from": f"{_display_name(message.sender_name)} vía Arrendi <{self.sender_address}>",
            "to": [message.to],
            "reply_to": message.reply_to,
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
        }
        if message.bcc:
            body["bcc"] = [message.bcc]
        if message.attachments:
            body["attachments"] = [
                {
                    "filename": attachment.filename,
                    "content": base64.b64encode(attachment.content).decode(),
                    "content_type": attachment.content_type,
                }
                for attachment in message.attachments
            ]
        headers = {"Idempotency-Key": message.idempotency_key} if message.idempotency_key else {}
        try:
            response = self.client.post(RESEND_URL, json=body, headers=headers)
        except httpx2.HTTPError as error:
            raise EmailError(str(error)) from error
        if response.is_error:
            raise EmailError(f"the provider answered {response.status_code}")
        try:
            return str(response.json()["id"])
        except (ValueError, KeyError) as error:
            raise EmailError("the provider did not return an id") from error


class DivertingSender:
    """Sends every email to the test inbox instead of to whom it was meant for."""

    def __init__(self, sender: EmailSender, test_inbox: str) -> None:
        self.sender = sender
        self.test_inbox = test_inbox

    def send(self, message: EmailMessage) -> str:
        return self.sender.send(
            replace(
                message,
                to=self.test_inbox,
                # The copy would be a second email to a real person.
                bcc=None,
                subject=f"[Para {message.to}] {message.subject}",
            )
        )


class RefusingSender:
    """Sends nothing. What is left when sending could reach someone it should not."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def send(self, message: EmailMessage) -> str:
        raise EmailError(self.reason)


def build_sender(settings: Settings, transport: httpx2.BaseTransport | None = None) -> EmailSender:
    """The sender for this environment.

    While a test inbox is set, every email goes there, in production too. Outside
    production the test inbox is required: without it nothing is sent, so a missing
    variable can never mean an email to a real tenant.
    """
    if not settings.email_api_key or not settings.email_sender:
        return RefusingSender("EMAIL_API_KEY and EMAIL_SENDER are not set")
    sender = ResendSender(settings.email_api_key, settings.email_sender, transport)
    if settings.email_test_inbox:
        return DivertingSender(sender, settings.email_test_inbox)
    if settings.environment != "production":
        return RefusingSender("EMAIL_TEST_INBOX is not set outside production")
    return sender
