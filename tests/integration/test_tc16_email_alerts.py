"""
TC-16 — email alert delivery on health threshold breach.

Satisfies Req-Func-Sw-17 and Test-Case-16 from CLAUDE.md §14.

Spins up an aiosmtpd in-process SMTP sink, points server.alerts at it,
triggers a below-threshold health score, and asserts the handler actually
received a message.
"""
import asyncio
import threading
import time
from contextlib import contextmanager

import pytest


@contextmanager
def smtp_sink(port: int = 11025):
    """In-process SMTP that collects incoming messages for assertion."""
    try:
        from aiosmtpd.controller import Controller  # type: ignore
    except ImportError:
        pytest.skip("aiosmtpd not installed")

    received: list = []

    class Handler:
        async def handle_DATA(self, server, session, envelope):
            received.append({
                "from": envelope.mail_from,
                "to": envelope.rcpt_tos,
                "data": envelope.content.decode("utf-8", errors="replace"),
            })
            return "250 OK"

    controller = Controller(Handler(), hostname="127.0.0.1", port=port)
    controller.start()
    try:
        yield received
    finally:
        controller.stop()


def test_tc16_email_alert_fires_on_threshold_breach(monkeypatch):
    port = 11025
    monkeypatch.setenv("ALERT_EMAIL_SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("ALERT_EMAIL_SMTP_PORT", str(port))
    monkeypatch.setenv("ALERT_EMAIL_FROM", "pathwise@test.local")
    monkeypatch.setenv("ALERT_EMAIL_TO", "oncall@test.local")
    monkeypatch.setenv("HEALTH_SCORE_THRESHOLD", "70")
    monkeypatch.setenv("ALERT_SUPPRESSION_WINDOW_S", "0")

    # Import after env vars are set so module-level constants pick them up.
    import importlib
    from server import alerts as alerts_module
    importlib.reload(alerts_module)

    with smtp_sink(port=port) as inbox:
        alert = alerts_module.check_and_alert(
            link_id="fiber-primary",
            health_score=35.0,
            confidence=0.92,
        )
        # Give the SMTP handler a moment to process
        time.sleep(0.3)

        assert alert is not None, "Alert should have been created"
        assert alert.health_score == 35.0
        assert len(inbox) >= 1, f"Expected at least one email, got {len(inbox)}"
        msg = inbox[0]
        assert "fiber-primary" in msg["data"]
        assert "35" in msg["data"]


def test_tc16_suppression_window_blocks_duplicate_alerts(monkeypatch):
    port = 11026
    monkeypatch.setenv("ALERT_EMAIL_SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("ALERT_EMAIL_SMTP_PORT", str(port))
    monkeypatch.setenv("ALERT_EMAIL_FROM", "pathwise@test.local")
    monkeypatch.setenv("ALERT_EMAIL_TO", "oncall@test.local")
    monkeypatch.setenv("HEALTH_SCORE_THRESHOLD", "70")
    monkeypatch.setenv("ALERT_SUPPRESSION_WINDOW_S", "60")

    import importlib
    from server import alerts as alerts_module
    importlib.reload(alerts_module)

    with smtp_sink(port=port) as inbox:
        a1 = alerts_module.check_and_alert("broadband-secondary", 30.0, 0.9)
        a2 = alerts_module.check_and_alert("broadband-secondary", 29.0, 0.9)
        time.sleep(0.3)
        assert a1 is not None
        # Second call should be suppressed
        assert a2 is None
        # Only one email should have been delivered
        assert len(inbox) == 1
