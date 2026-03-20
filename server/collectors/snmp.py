"""
SNMP v2c collector — polls managed network devices for telemetry.

Satisfies Req-Func-Sw-20 (accept telemetry via SNMP v2c+).

Uses pysnmp to poll standard IF-MIB counters at 1 Hz:
  - IF-MIB::ifHCInOctets.<ifIndex>    (bytes received, 64-bit)
  - IF-MIB::ifHCOutOctets.<ifIndex>   (bytes sent, 64-bit)
  - IF-MIB::ifInDiscards.<ifIndex>    (drops, used for packet_loss)
  - IF-MIB::ifOutDiscards.<ifIndex>
  - IF-MIB::ifSpeed.<ifIndex>         (link speed for bandwidth_util_pct)

Latency/jitter are derived from the spread between consecutive SNMP
round-trip response times, since most layer-2 interfaces do not expose
an OID for RTT directly. When an ICMP probe target is configured, we
use real ping RTT as a fallback for those two metrics.
"""

from __future__ import annotations
import asyncio
import os
import statistics
import time
from dataclasses import dataclass
from typing import Optional

from server.state import TelemetryPoint
from server.collectors.base import BaseCollector, run_ping


# Standard IF-MIB OIDs (RFC 2863)
OID_IF_HC_IN_OCTETS  = "1.3.6.1.2.1.31.1.1.1.6"    # ifHCInOctets
OID_IF_HC_OUT_OCTETS = "1.3.6.1.2.1.31.1.1.1.10"   # ifHCOutOctets
OID_IF_IN_DISCARDS   = "1.3.6.1.2.1.2.2.1.13"      # ifInDiscards
OID_IF_OUT_DISCARDS  = "1.3.6.1.2.1.2.2.1.19"      # ifOutDiscards
OID_IF_HC_IN_UCAST   = "1.3.6.1.2.1.31.1.1.1.7"    # ifHCInUcastPkts
OID_IF_HC_OUT_UCAST  = "1.3.6.1.2.1.31.1.1.1.11"   # ifHCOutUcastPkts
OID_IF_SPEED         = "1.3.6.1.2.1.2.2.1.5"       # ifSpeed (bits/s)
OID_IF_HIGH_SPEED    = "1.3.6.1.2.1.31.1.1.1.15"   # ifHighSpeed (Mbps)


@dataclass
class SNMPSample:
    """Raw counters from one SNMP poll."""
    in_octets: int
    out_octets: int
    in_discards: int
    out_discards: int
    in_ucast: int
    out_ucast: int
    link_speed_mbps: float
    rtt_ms: float
    ts: float


async def _snmp_get_int(host: str, community: str, oid: str,
                        port: int = 161) -> Optional[int]:
    """Return integer value of an OID, or None on failure."""
    from server.collectors.base import snmp_get
    raw = await snmp_get(host, community, oid, port)
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


async def _poll_sample(host: str, community: str, if_index: int,
                       port: int) -> Optional[SNMPSample]:
    """One full poll of the IF-MIB counters for a given interface."""
    t0 = time.perf_counter()

    async def g(oid: str) -> Optional[int]:
        return await _snmp_get_int(host, community, f"{oid}.{if_index}", port)

    in_oct  = await g(OID_IF_HC_IN_OCTETS)
    out_oct = await g(OID_IF_HC_OUT_OCTETS)
    in_disc = await g(OID_IF_IN_DISCARDS)
    out_disc = await g(OID_IF_OUT_DISCARDS)
    in_u    = await g(OID_IF_HC_IN_UCAST)
    out_u   = await g(OID_IF_HC_OUT_UCAST)

    # Prefer ifHighSpeed (Mbps) over ifSpeed (bits/s) — RFC 2863 recommends
    # ifHighSpeed for interfaces > 10 Gbit/s.
    high_speed = await g(OID_IF_HIGH_SPEED)
    if high_speed:
        speed_mbps = float(high_speed)
    else:
        speed_bps = await g(OID_IF_SPEED)
        speed_mbps = float(speed_bps) / 1_000_000 if speed_bps else 100.0

    rtt_ms = (time.perf_counter() - t0) * 1000

    if in_oct is None or out_oct is None:
        return None

    return SNMPSample(
        in_octets=in_oct,
        out_octets=out_oct,
        in_discards=in_disc or 0,
        out_discards=out_disc or 0,
        in_ucast=in_u or 0,
        out_ucast=out_u or 0,
        link_speed_mbps=speed_mbps or 100.0,
        rtt_ms=rtt_ms,
        ts=time.time(),
    )


class SNMPCollector(BaseCollector):
    """
    SNMP v2c telemetry collector — polls a managed device over UDP 161
    and builds a TelemetryPoint from the delta between consecutive samples.

    Configure via env per link:
      <LINK>_SNMP_HOST       — target IP/hostname (required)
      <LINK>_SNMP_COMMUNITY  — community string (default "public")
      <LINK>_SNMP_IF_INDEX   — interface index (default 1)
      <LINK>_SNMP_PORT       — UDP port (default 161)
      <LINK>_PING_TARGET     — optional ICMP target for real RTT (default 8.8.8.8)

    Example:
      FIBER_SNMP_HOST=192.168.1.1
      FIBER_SNMP_COMMUNITY=public
      FIBER_SNMP_IF_INDEX=2
    """

    def __init__(self, link_id: str, env_prefix: str):
        super().__init__(link_id)
        self.host = os.environ.get(f"{env_prefix}_SNMP_HOST", "")
        self.community = os.environ.get(f"{env_prefix}_SNMP_COMMUNITY", "public")
        self.if_index = int(os.environ.get(f"{env_prefix}_SNMP_IF_INDEX", "1"))
        self.port = int(os.environ.get(f"{env_prefix}_SNMP_PORT", "161"))
        self.ping_target = os.environ.get(f"{env_prefix}_PING_TARGET", "8.8.8.8")
        self._last_sample: Optional[SNMPSample] = None
        self._rtt_history: list[float] = []

    async def collect(self) -> TelemetryPoint:
        if not self.host:
            raise RuntimeError(
                f"SNMPCollector for {self.link_id}: no SNMP host configured"
            )

        curr = await _poll_sample(self.host, self.community, self.if_index, self.port)
        if curr is None:
            raise RuntimeError(f"SNMP poll returned no data from {self.host}")

        # First poll — need a baseline for delta calculations.
        if self._last_sample is None:
            self._last_sample = curr
            # Return a neutral point so the 1 Hz loop can continue.
            return TelemetryPoint(
                timestamp=curr.ts, link_id=self.link_id,
                latency_ms=curr.rtt_ms, jitter_ms=0.0, packet_loss_pct=0.0,
                bandwidth_util_pct=0.0, rtt_ms=curr.rtt_ms,
            )

        prev = self._last_sample
        dt = max(curr.ts - prev.ts, 0.001)

        d_bytes = (curr.in_octets - prev.in_octets) + (curr.out_octets - prev.out_octets)
        throughput_mbps = (d_bytes * 8) / (dt * 1_000_000)
        util_pct = 100 * throughput_mbps / max(curr.link_speed_mbps, 1.0)

        d_ucast = max((curr.in_ucast - prev.in_ucast) + (curr.out_ucast - prev.out_ucast), 1)
        d_disc = (curr.in_discards - prev.in_discards) + (curr.out_discards - prev.out_discards)
        loss_pct = 100 * d_disc / d_ucast if d_ucast else 0.0

        # For latency/jitter, fall back to ICMP if a ping target is configured
        # because SNMP RTT reflects the device management path, not the WAN.
        if self.ping_target:
            try:
                pr = await run_ping(self.ping_target, count=3, timeout_ms=1000)
                latency_ms = pr.avg_latency_ms or curr.rtt_ms
                jitter_ms = pr.jitter_ms
                icmp_loss = pr.packet_loss_pct
                # Blend ICMP loss with SNMP discard ratio — take the larger
                loss_pct = max(loss_pct, icmp_loss)
            except Exception:
                latency_ms = curr.rtt_ms
                jitter_ms = 0.0
        else:
            latency_ms = curr.rtt_ms
            # Build jitter from RTT history
            self._rtt_history.append(curr.rtt_ms)
            if len(self._rtt_history) > 20:
                self._rtt_history.pop(0)
            jitter_ms = statistics.stdev(self._rtt_history) if len(self._rtt_history) > 1 else 0.0

        self._last_sample = curr

        return TelemetryPoint(
            timestamp=curr.ts,
            link_id=self.link_id,
            latency_ms=max(latency_ms, 0.1),
            jitter_ms=max(jitter_ms, 0.0),
            packet_loss_pct=max(min(loss_pct, 100.0), 0.0),
            bandwidth_util_pct=max(min(util_pct, 100.0), 0.0),
            rtt_ms=max(latency_ms, 0.1),
        )


async def self_test(host: str, community: str = "public", if_index: int = 1) -> dict:
    """CLI self-test — poll a single sample and report."""
    s = await _poll_sample(host, community, if_index, port=161)
    if s is None:
        return {"ok": False, "error": "no_response"}
    return {
        "ok": True,
        "host": host,
        "if_index": if_index,
        "in_octets": s.in_octets,
        "out_octets": s.out_octets,
        "link_speed_mbps": s.link_speed_mbps,
        "rtt_ms": round(s.rtt_ms, 2),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python -m server.collectors.snmp <host> [community] [if_index]")
        sys.exit(1)
    host = sys.argv[1]
    community = sys.argv[2] if len(sys.argv) > 2 else "public"
    if_index = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    result = asyncio.run(self_test(host, community, if_index))
    print(result)
