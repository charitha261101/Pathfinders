"""
Redis pub/sub broker — PathWise AI inter-service event bus.

Implements the channel contract defined in CLAUDE.md §6.3:
  pathwise:telemetry:{link_id}    — raw telemetry stream
  pathwise:alerts:{site_id}       — health score threshold breach alerts
  pathwise:validation:request     — routing change proposals to sandbox
  pathwise:validation:result      — sandbox PASSED/FAILED results
  pathwise:steering:trigger       — steering engine activation events
  pathwise:dashboard:updates      — WebSocket broadcast to dashboard clients

Satisfies Req-Qual-Sec-1 (rediss:// TLS) when REDIS_URL starts with rediss://.
Gracefully no-ops if Redis is unavailable — callers continue with
in-process state instead of failing.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Any, AsyncIterator, Callable, Optional

logger = logging.getLogger("pathwise.redis")

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
REDIS_TLS_CA = os.environ.get("REDIS_TLS_CA")  # Optional CA for rediss://

# Channel names
CH_TELEMETRY   = "pathwise:telemetry:{link_id}"
CH_ALERTS      = "pathwise:alerts:{site_id}"
CH_VALIDATION_REQ = "pathwise:validation:request"
CH_VALIDATION_RES = "pathwise:validation:result"
CH_STEERING    = "pathwise:steering:trigger"
CH_DASHBOARD   = "pathwise:dashboard:updates"


class RedisBroker:
    """
    Thin async wrapper around redis-py asyncio client. Falls back to a
    local in-process pub/sub if Redis can't be reached.
    """

    def __init__(self, url: str = REDIS_URL):
        self.url = url
        self._client = None
        self._pubsub = None
        self._fallback_subs: dict[str, list[asyncio.Queue]] = {}
        self._connected = False

    async def connect(self) -> bool:
        """Attempt to connect. Returns True on success."""
        try:
            import redis.asyncio as redis_async  # type: ignore
            kwargs = {}
            if self.url.startswith("rediss://") and REDIS_TLS_CA:
                kwargs["ssl_ca_certs"] = REDIS_TLS_CA
            self._client = redis_async.from_url(self.url, **kwargs,
                                                decode_responses=True)
            await self._client.ping()
            self._connected = True
            logger.info("Redis broker connected: %s", self.url)
            return True
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — pub/sub will run in-process", exc)
            self._connected = False
            self._client = None
            return False

    async def close(self):
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
        self._client = None
        self._connected = False

    # ── Publish ────────────────────────────────────────────

    async def publish(self, channel: str, payload: Any) -> int:
        """Publish a message. Returns the number of subscribers (0 if offline)."""
        msg = json.dumps(payload, default=str)
        if self._connected and self._client:
            try:
                return int(await self._client.publish(channel, msg))
            except Exception as exc:
                logger.warning("Redis publish error on %s: %s", channel, exc)
        # Fallback — deliver to in-process subscribers
        queues = self._fallback_subs.get(channel, [])
        for q in queues:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass
        return len(queues)

    async def publish_telemetry(self, link_id: str, point: dict) -> int:
        return await self.publish(CH_TELEMETRY.format(link_id=link_id), point)

    async def publish_alert(self, site_id: str, alert: dict) -> int:
        return await self.publish(CH_ALERTS.format(site_id=site_id), alert)

    async def publish_validation_request(self, request: dict) -> int:
        return await self.publish(CH_VALIDATION_REQ, request)

    async def publish_validation_result(self, result: dict) -> int:
        return await self.publish(CH_VALIDATION_RES, result)

    async def publish_steering(self, event: dict) -> int:
        return await self.publish(CH_STEERING, event)

    async def publish_dashboard(self, update: dict) -> int:
        return await self.publish(CH_DASHBOARD, update)

    # ── Subscribe ──────────────────────────────────────────

    async def subscribe(self, channel: str) -> AsyncIterator[dict]:
        """
        Async generator yielding parsed JSON messages for a channel.
        Transparently uses Redis or in-process fallback.
        """
        if self._connected and self._client:
            pubsub = self._client.pubsub()
            await pubsub.subscribe(channel)
            try:
                async for message in pubsub.listen():
                    if message.get("type") == "message":
                        try:
                            yield json.loads(message["data"])
                        except Exception:
                            yield {"raw": message["data"]}
            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
        else:
            queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
            self._fallback_subs.setdefault(channel, []).append(queue)
            try:
                while True:
                    raw = await queue.get()
                    try:
                        yield json.loads(raw)
                    except Exception:
                        yield {"raw": raw}
            finally:
                self._fallback_subs.get(channel, []).remove(queue)


_broker: Optional[RedisBroker] = None


async def get_broker() -> RedisBroker:
    global _broker
    if _broker is None:
        _broker = RedisBroker()
        await _broker.connect()
    return _broker


def publish_sync(channel: str, payload: Any) -> None:
    """
    Convenience for sync callers (e.g. inside synchronous route handlers).
    Dispatches to the async publish and drops the result.
    """
    async def _run():
        b = await get_broker()
        await b.publish(channel, payload)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        # No running loop — run synchronously
        asyncio.run(_run())
