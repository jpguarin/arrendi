"""Sending through Resend, and the rule that keeps test emails away from real tenants."""

import base64
import json
from dataclasses import replace

import httpx2
import pytest

from app.config import Settings
from app.email.content import BRAND_MARK, BRAND_MARK_CID
from app.email.sender import (
    Attachment,
    EmailError,
    EmailMessage,
    ResendSender,
    build_sender,
)

MESSAGE = EmailMessage(
    to="carlos@example.com",
    sender_name="Ana Gómez",
    reply_to="ana@example.com",
    subject="Cuenta de cobro N.º 0031",
    html="<p>Hola</p>",
    text="Hola",
    attachments=[Attachment("cuenta-0031.pdf", b"%PDF-1.4", "application/pdf")],
    bcc="ana@example.com",
    idempotency_key="notification-1",
)


def recording(response: httpx2.Response) -> tuple[httpx2.MockTransport, list[httpx2.Request]]:
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return response

    return httpx2.MockTransport(handle), requests


def settings(**overrides: str) -> Settings:
    values = {
        "environment": "local",
        "email_api_key": "re_test",
        "email_sender": "cuentas@arrendi.test",
        "email_test_inbox": "",
    } | overrides
    return Settings(_env_file=None, **values)


def test_the_isotipo_travels_inline_when_the_html_shows_it() -> None:
    transport, requests = recording(httpx2.Response(200, json={"id": "abc-123"}))
    message = replace(MESSAGE, html=f'<img src="cid:{BRAND_MARK_CID}">', attachments=[])

    ResendSender("re_test", "cuentas@arrendi.test", transport).send(message)

    (request,) = requests
    assert json.loads(request.content)["attachments"] == [
        {
            "filename": "arrendi.png",
            "content": base64.b64encode(BRAND_MARK).decode(),
            "content_type": "image/png",
            "content_id": BRAND_MARK_CID,
        }
    ]


def test_resend_gets_the_whole_message() -> None:
    transport, requests = recording(httpx2.Response(200, json={"id": "abc-123"}))

    provider_id = ResendSender("re_test", "cuentas@arrendi.test", transport).send(MESSAGE)

    assert provider_id == "abc-123"
    (request,) = requests
    assert (request.method, str(request.url)) == ("POST", "https://api.resend.com/emails")
    assert request.headers["authorization"] == "Bearer re_test"
    assert request.headers["idempotency-key"] == "notification-1"
    assert json.loads(request.content) == {
        "from": "Ana Gómez vía Arrendi <cuentas@arrendi.test>",
        "to": ["carlos@example.com"],
        "reply_to": "ana@example.com",
        "subject": "Cuenta de cobro N.º 0031",
        "html": "<p>Hola</p>",
        "text": "Hola",
        "bcc": ["ana@example.com"],
        "attachments": [
            {
                "filename": "cuenta-0031.pdf",
                "content": base64.b64encode(b"%PDF-1.4").decode(),
                "content_type": "application/pdf",
            }
        ],
    }


def test_owner_name_cannot_break_the_from_header() -> None:
    transport, requests = recording(httpx2.Response(200, json={"id": "x"}))
    message = EmailMessage(
        to="c@example.com",
        sender_name='Ana" <otra@example.com>\r\nBcc: x',
        reply_to="ana@example.com",
        subject="s",
        html="h",
        text="t",
    )

    ResendSender("re_test", "cuentas@arrendi.test", transport).send(message)

    sender = json.loads(requests[0].content)["from"]
    assert sender.endswith(" vía Arrendi <cuentas@arrendi.test>")
    assert sender.count("<") == 1 and "\n" not in sender and '"' not in sender


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(429, json={"message": "rate limit"}),
        httpx2.Response(500),
        httpx2.Response(200, json={"unexpected": True}),
    ],
)
def test_provider_problem_is_an_email_error(response: httpx2.Response) -> None:
    transport, _ = recording(response)

    with pytest.raises(EmailError):
        ResendSender("re_test", "cuentas@arrendi.test", transport).send(MESSAGE)


def test_connection_problem_is_an_email_error() -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("no network")

    with pytest.raises(EmailError):
        ResendSender("re_test", "c@arrendi.test", httpx2.MockTransport(fail)).send(MESSAGE)


# Who really gets the email


@pytest.mark.parametrize("environment", ["local", "preview", "production"])
def test_with_a_test_inbox_everything_goes_there(environment: str) -> None:
    transport, requests = recording(httpx2.Response(200, json={"id": "x"}))
    sender = build_sender(
        settings(environment=environment, email_test_inbox="pruebas@example.com"), transport
    )

    sender.send(MESSAGE)

    body = json.loads(requests[0].content)
    assert body["to"] == ["pruebas@example.com"]
    # The copy is dropped, and the subject says who it was meant for.
    assert "bcc" not in body
    assert body["subject"] == "[Para carlos@example.com] Cuenta de cobro N.º 0031"
    assert "carlos@example.com" not in json.dumps([body["to"], body.get("cc"), body.get("bcc")])


@pytest.mark.parametrize("environment", ["local", "preview"])
def test_outside_production_nothing_is_sent_without_a_test_inbox(environment: str) -> None:
    transport, requests = recording(httpx2.Response(200, json={"id": "x"}))
    sender = build_sender(settings(environment=environment), transport)

    with pytest.raises(EmailError):
        sender.send(MESSAGE)

    assert requests == []


def test_production_without_a_test_inbox_sends_to_the_tenant() -> None:
    transport, requests = recording(httpx2.Response(200, json={"id": "x"}))

    build_sender(settings(environment="production"), transport).send(MESSAGE)

    body = json.loads(requests[0].content)
    assert (body["to"], body["bcc"]) == (["carlos@example.com"], ["ana@example.com"])


@pytest.mark.parametrize("missing", ["email_api_key", "email_sender"])
def test_without_the_provider_configured_nothing_is_sent(missing: str) -> None:
    transport, requests = recording(httpx2.Response(200, json={"id": "x"}))
    sender = build_sender(settings(environment="production", **{missing: ""}), transport)

    with pytest.raises(EmailError):
        sender.send(MESSAGE)

    assert requests == []
