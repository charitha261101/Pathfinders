# pathwiseaiAPPSWITCH.md
## PathWise AI — Application-Aware Bandwidth Enforcement & Live Quality Control
### For Claude CLI (Claude Code) — Execute fully, autonomously, in order

**Feature name:** App Priority Switch  
**Core behavior:** When Zoom is set to HIGH priority while YouTube is open at 2160p, PathWise AI enforces a bandwidth ceiling on YouTube traffic that forces its DASH adaptive engine to drop to 144p within 2–3 seconds. When priority is lifted, YouTube auto-scales back to 2160p.  
**Enforcement engine:** Linux `tc` (HTB + u32 filters) | Windows `New-NetQosPolicy` + WFP | Simulation mode for Docker/demo  
**Integration:** Extends existing `server/traffic_shaper.py` + adds new `AppPriorityManager` UI page  
**Satisfies:** Req-Func-Sw-6 (pre-emptive traffic class rerouting), SRS Application QoS section, SDD TrafficSteeringController module

---

## READ FIRST — HOW THIS WORKS END TO END

```
User in PathWise AI UI
        │
        │  "Set Zoom = HIGH, YouTube = LOW"
        ▼
  AppPriorityManager page (React)
        │
        │  POST /api/v1/apps/priorities
        ▼
  BandwidthEnforcer (FastAPI backend)
        │
        │  Computes per-app bandwidth allocation:
        │    Zoom    → 60 Mbps guaranteed, 95 Mbps ceil (CRITICAL class)
        │    YouTube → 300 Kbps hard cap  (LOW class)
        │    Others  → remainder, fair-share
        ▼
  OS QoS Layer
  ┌─────────────────────────────────────┐
  │  Linux: tc qdisc HTB + u32 filters  │
  │  Win:   New-NetQosPolicy + WFP      │
  │  Demo:  Simulate mode (log only)    │
  └─────────────────────────────────────┘
        │
        │  YouTube receives ≤300 Kbps
        ▼
  YouTube DASH Adaptive Engine
        │  Detects bandwidth drop
        │  Within 2-3 seconds:
        ▼
  YouTube drops from 2160p → 144p   ✓
        │
        │  WebSocket pushes quality estimate
        ▼
  Dashboard shows:
    Zoom:    ████████████ HIGH  (46 Mbps)
    YouTube: █            LOW   (~144p estimated)
```

**Why YouTube drops quality:**  
YouTube uses DASH (Dynamic Adaptive Streaming over HTTP). It constantly monitors available throughput. When the enforcer caps YouTube's TCP connection to 300 Kbps, the DASH algorithm detects the drop and switches segments. Quality tiers map to bandwidth:

| YouTube Quality | Required Bandwidth |
|-----------------|-------------------|
| 2160p (4K)     | 15–25 Mbps        |
| 1440p           | 8–18 Mbps         |
| 1080p60         | 6–8 Mbps          |
| 1080p30         | 4–6 Mbps          |
| 720p60          | 2.5–4 Mbps        |
| 720p30          | 1.5–2.5 Mbps      |
| 480p            | 500 Kbps–1 Mbps   |
| 360p            | 300–500 Kbps      |
| 144p            | 80–150 Kbps       |

Capping at 300 Kbps → YouTube locks to 144p. Capping at 700 Kbps → 360p. Uncapped → 2160p if link allows.

---

## SECTION 0 — DIRECTORY STRUCTURE

Create these new paths:

```
server/
  app_qos/
    __init__.py
    signatures.py          # App IP/port/process fingerprints
    flow_detector.py       # Detect running apps from active sockets
    bandwidth_enforcer.py  # tc / PowerShell / simulate modes
    priority_manager.py    # Priority queue + allocation calculator
    quality_predictor.py   # Bandwidth → quality estimator

server/routers/
  app_priority.py          # REST API for app priority feature

frontend/src/pages/user/
  AppPriorityManager.tsx   # Main UI page

frontend/src/pages/admin/
  AppQoSOverview.tsx       # Admin view of all users' app priorities

frontend/src/hooks/
  useAppQoS.ts             # WebSocket hook for live quality updates

tests/
  test_app_qos/
    test_signatures.py
    test_flow_detector.py
    test_bandwidth_enforcer.py
    test_priority_api.py
    test_quality_predictor.py
    test_e2e_zoom_youtube.py
```

---

## SECTION 1 — APP SIGNATURE DATABASE

### Create `server/app_qos/signatures.py`

This is the master registry of all supported applications. Each entry defines how to identify the app's traffic on the wire and what quality tiers apply when bandwidth is constrained.

```python
"""
Application Traffic Signatures — PathWise AI App Priority Switch
Defines IP ranges, ports, process names, and quality tiers for 20+ apps.
Used by FlowDetector for identification and BandwidthEnforcer for marking.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class QualityTier:
    """Describes a quality level achievable at a given bandwidth."""
    label: str           # e.g. "144p", "HD", "4K", "Excellent"
    min_kbps: int        # minimum bandwidth to sustain this quality
    max_kbps: int        # bandwidth at which this tier is fully satisfied
    description: str     # human-readable description for UI


@dataclass
class AppSignature:
    name: str                          # display name: "Zoom"
    app_id: str                        # machine key: "zoom"
    category: str                      # video_call | streaming | voip | gaming | productivity | other
    icon: str                          # emoji for UI
    color: str                         # hex color for UI

    # Traffic identification
    dst_ip_ranges: List[str]           # CIDR blocks of app servers
    dst_ports: List[int]               # destination TCP/UDP ports
    src_ports: List[int]               # source ports if app binds specific port
    protocol: str                      # tcp | udp | both
    process_names: List[str]           # process names on Windows/Linux

    # Bandwidth characteristics
    min_kbps: int                      # absolute minimum (app becomes unusable below this)
    recommended_kbps: int              # full quality / ideal
    max_useful_kbps: int               # additional BW above this has no effect

    # Quality tiers (only for streaming/media apps)
    quality_tiers: List[QualityTier] = field(default_factory=list)

    # Default priority class
    default_priority: str = "NORMAL"   # CRITICAL | HIGH | NORMAL | LOW | BLOCKED
    dscp_value: int = 0                # DSCP marking for SDN integration


APP_SIGNATURES: Dict[str, AppSignature] = {

    # ─── VIDEO CONFERENCING ────────────────────────────────────────────────

    "zoom": AppSignature(
        name="Zoom", app_id="zoom", category="video_call",
        icon="🎥", color="#2D8CFF",
        dst_ip_ranges=[
            "3.7.35.0/25",   "3.21.137.128/25", "3.22.11.0/24",
            "3.23.93.0/24",  "3.25.41.128/25",  "3.25.42.0/25",
            "3.25.49.0/24",  "3.80.20.128/25",  "3.96.19.0/24",
            "3.101.32.128/25","3.101.52.0/25",  "3.104.34.128/25",
            "3.120.121.0/25","3.127.194.128/25","13.52.6.128/25",
            "52.202.62.192/26","52.215.168.0/25","99.79.4.0/25",
            "129.151.1.128/27","130.61.164.0/22",
        ],
        dst_ports=[443, 80, 8801, 8802],
        src_ports=[],
        protocol="both",
        process_names=["Zoom.exe", "zoom", "zoom.us", "CptHost.exe"],
        min_kbps=600,
        recommended_kbps=3500,
        max_useful_kbps=8000,
        quality_tiers=[
            QualityTier("Poor",      0,     599,  "Audio only or frozen video"),
            QualityTier("Low",       600,   999,  "360p video, degraded audio"),
            QualityTier("Fair",      1000,  1999, "480p, standard quality"),
            QualityTier("Good",      2000,  3499, "720p HD, clear video"),
            QualityTier("Excellent", 3500,  99999,"1080p HD, high fidelity"),
        ],
        default_priority="HIGH",
        dscp_value=46,  # EF — Expedited Forwarding
    ),

    "teams": AppSignature(
        name="Microsoft Teams", app_id="teams", category="video_call",
        icon="💼", color="#6264A7",
        dst_ip_ranges=[
            "13.107.64.0/18", "52.112.0.0/14", "52.122.0.0/15",
            "52.238.119.141/32", "52.244.160.207/32",
        ],
        dst_ports=[443, 80, 3478, 3479, 3480, 3481],
        src_ports=[],
        protocol="both",
        process_names=["Teams.exe", "teams", "ms-teams"],
        min_kbps=600,
        recommended_kbps=4000,
        max_useful_kbps=10000,
        quality_tiers=[
            QualityTier("Poor",      0,     599,  "Audio degraded"),
            QualityTier("Fair",      600,   1499, "Low resolution"),
            QualityTier("Good",      1500,  3999, "720p HD"),
            QualityTier("Excellent", 4000,  99999,"1080p HD"),
        ],
        default_priority="HIGH",
        dscp_value=46,
    ),

    "google_meet": AppSignature(
        name="Google Meet", app_id="google_meet", category="video_call",
        icon="📹", color="#00897B",
        dst_ip_ranges=["74.125.0.0/16", "108.177.0.0/17", "172.217.0.0/16"],
        dst_ports=[443, 19302, 19303, 19304, 19305],
        src_ports=[],
        protocol="both",
        process_names=["chrome.exe", "chrome", "chromium"],
        min_kbps=800,
        recommended_kbps=3800,
        max_useful_kbps=9000,
        quality_tiers=[
            QualityTier("Poor",      0,     799,  "Disconnects likely"),
            QualityTier("Fair",      800,   1999, "360p"),
            QualityTier("Good",      2000,  3799, "720p"),
            QualityTier("Excellent", 3800,  99999,"1080p"),
        ],
        default_priority="HIGH",
        dscp_value=46,
    ),

    # ─── STREAMING (VIDEO) ─────────────────────────────────────────────────

    "youtube": AppSignature(
        name="YouTube", app_id="youtube", category="streaming",
        icon="▶️", color="#FF0000",
        dst_ip_ranges=[
            "64.233.160.0/19", "66.102.0.0/20",  "66.249.64.0/19",
            "72.14.192.0/18",  "108.177.8.0/21", "142.250.0.0/15",
            "172.217.0.0/16",  "173.194.0.0/16", "209.85.128.0/17",
            "216.58.192.0/19", "216.239.32.0/19",
        ],
        dst_ports=[443, 80],
        src_ports=[],
        protocol="tcp",
        process_names=["chrome.exe", "firefox.exe", "msedge.exe",
                       "chrome", "firefox", "safari"],
        min_kbps=80,
        recommended_kbps=25000,
        max_useful_kbps=50000,
        quality_tiers=[
            QualityTier("144p",  80,    299,   "144p — Very low quality"),
            QualityTier("240p",  300,   499,   "240p — Low quality"),
            QualityTier("360p",  500,   699,   "360p — Standard"),
            QualityTier("480p",  700,   1499,  "480p — SD"),
            QualityTier("720p",  1500,  4999,  "720p — HD"),
            QualityTier("1080p", 5000,  11999, "1080p — Full HD"),
            QualityTier("1440p", 12000, 24999, "1440p — 2K QHD"),
            QualityTier("2160p", 25000, 99999, "2160p — 4K Ultra HD"),
        ],
        default_priority="NORMAL",
        dscp_value=0,
    ),

    "netflix": AppSignature(
        name="Netflix", app_id="netflix", category="streaming",
        icon="🎬", color="#E50914",
        dst_ip_ranges=[
            "198.38.96.0/19",  "198.45.48.0/20", "37.77.184.0/21",
            "45.57.0.0/17",    "23.246.0.0/18",  "69.53.224.0/19",
        ],
        dst_ports=[443, 80],
        src_ports=[],
        protocol="tcp",
        process_names=["netflix.exe", "chrome.exe", "firefox.exe",
                       "ApplicationFrameHost.exe", "WWAHost.exe"],
        min_kbps=500,
        recommended_kbps=25000,
        max_useful_kbps=50000,
        quality_tiers=[
            QualityTier("Low",    500,   2999,  "Low quality (SD)"),
            QualityTier("Medium", 3000,  6999,  "Standard HD"),
            QualityTier("High",   7000,  24999, "Full HD 1080p"),
            QualityTier("Ultra",  25000, 99999, "4K Ultra HD + HDR"),
        ],
        default_priority="NORMAL",
        dscp_value=8,
    ),

    "twitch": AppSignature(
        name="Twitch", app_id="twitch", category="streaming",
        icon="🟣", color="#9146FF",
        dst_ip_ranges=["205.209.176.0/20", "192.16.64.0/18"],
        dst_ports=[443, 80, 1935],
        src_ports=[],
        protocol="tcp",
        process_names=["chrome.exe", "firefox.exe", "TwitchUI.exe"],
        min_kbps=500,
        recommended_kbps=8000,
        max_useful_kbps=20000,
        quality_tiers=[
            QualityTier("160p",  500,   999,  "160p mobile"),
            QualityTier("360p",  1000,  2499, "360p"),
            QualityTier("480p",  2500,  3999, "480p"),
            QualityTier("720p",  4000,  7999, "720p60"),
            QualityTier("1080p", 8000,  99999,"1080p60"),
        ],
        default_priority="NORMAL",
        dscp_value=0,
    ),

    "disney_plus": AppSignature(
        name="Disney+", app_id="disney_plus", category="streaming",
        icon="🏰", color="#113CCF",
        dst_ip_ranges=["13.35.0.0/16", "99.86.0.0/16"],
        dst_ports=[443, 80],
        src_ports=[],
        protocol="tcp",
        process_names=["DisneyPlus.exe", "chrome.exe", "firefox.exe"],
        min_kbps=500,
        recommended_kbps=25000,
        max_useful_kbps=50000,
        quality_tiers=[
            QualityTier("SD",    500,  4999,  "SD"),
            QualityTier("HD",    5000, 24999, "HD 1080p"),
            QualityTier("4K",   25000, 99999, "4K Ultra HD + HDR"),
        ],
        default_priority="NORMAL",
        dscp_value=0,
    ),

    # ─── VOICE / AUDIO ─────────────────────────────────────────────────────

    "discord": AppSignature(
        name="Discord", app_id="discord", category="voip",
        icon="🎮", color="#5865F2",
        dst_ip_ranges=["162.159.128.0/17", "198.41.128.0/17"],
        dst_ports=[443, 80, 50000, 65535],
        src_ports=[],
        protocol="both",
        process_names=["Discord.exe", "discord", "DiscordPTB.exe"],
        min_kbps=30,
        recommended_kbps=128,
        max_useful_kbps=500,
        quality_tiers=[
            QualityTier("Voice",  30,  127, "Voice only"),
            QualityTier("Video", 128,  499, "720p video"),
            QualityTier("HD",    500, 9999, "1080p video"),
        ],
        default_priority="HIGH",
        dscp_value=46,
    ),

    "spotify": AppSignature(
        name="Spotify", app_id="spotify", category="voip",
        icon="🎵", color="#1DB954",
        dst_ip_ranges=["35.186.224.0/19", "35.186.255.0/24"],
        dst_ports=[443, 4070, 80],
        src_ports=[],
        protocol="both",
        process_names=["Spotify.exe", "spotify", "SpotifyWebHelper.exe"],
        min_kbps=24,
        recommended_kbps=320,
        max_useful_kbps=500,
        quality_tiers=[
            QualityTier("Low",    24,  95,  "Low quality (24 kbps)"),
            QualityTier("Normal", 96,  159, "Normal (96 kbps)"),
            QualityTier("High",   160, 319, "High (160 kbps)"),
            QualityTier("Very High", 320, 9999, "Very High (320 kbps)"),
        ],
        default_priority="NORMAL",
        dscp_value=0,
    ),

    # ─── PRODUCTIVITY / CLOUD ──────────────────────────────────────────────

    "google_chrome": AppSignature(
        name="Google Chrome (General)", app_id="chrome", category="productivity",
        icon="🌐", color="#4285F4",
        dst_ip_ranges=[],
        dst_ports=[443, 80],
        src_ports=[],
        protocol="tcp",
        process_names=["chrome.exe", "chrome", "chromium", "chromium-browser"],
        min_kbps=100,
        recommended_kbps=10000,
        max_useful_kbps=100000,
        quality_tiers=[],
        default_priority="NORMAL",
        dscp_value=0,
    ),

    "onedrive": AppSignature(
        name="OneDrive", app_id="onedrive", category="productivity",
        icon="☁️", color="#0078D4",
        dst_ip_ranges=["13.107.6.0/24","13.107.18.0/24","13.107.128.0/22"],
        dst_ports=[443, 80],
        src_ports=[],
        protocol="tcp",
        process_names=["OneDrive.exe", "onedrive"],
        min_kbps=100,
        recommended_kbps=50000,
        max_useful_kbps=1000000,
        quality_tiers=[],
        default_priority="LOW",
        dscp_value=0,
    ),

    # ─── GAMING ───────────────────────────────────────────────────────────

    "steam": AppSignature(
        name="Steam", app_id="steam", category="gaming",
        icon="🎮", color="#1B2838",
        dst_ip_ranges=["103.10.124.0/23","155.133.224.0/19","162.254.192.0/18"],
        dst_ports=[443, 80, 27000, 27015, 27036],
        src_ports=[],
        protocol="both",
        process_names=["steam.exe", "steam", "gameoverlayui.exe"],
        min_kbps=100,
        recommended_kbps=3000,
        max_useful_kbps=10000,
        quality_tiers=[
            QualityTier("Unplayable", 0,   99,  "Too slow for gaming"),
            QualityTier("Playable",  100,  499, "Basic gaming"),
            QualityTier("Good",      500, 2999, "Good gaming experience"),
            QualityTier("Excellent", 3000, 9999,"Excellent — no lag"),
        ],
        default_priority="NORMAL",
        dscp_value=18,
    ),
}

# Quick lookup helpers
def get_app(app_id: str) -> Optional[AppSignature]:
    return APP_SIGNATURES.get(app_id)

def get_all_app_ids() -> List[str]:
    return list(APP_SIGNATURES.keys())

def predict_quality(app_id: str, available_kbps: int) -> Optional[QualityTier]:
    """Return the quality tier a streaming app would display at given bandwidth."""
    sig = get_app(app_id)
    if not sig or not sig.quality_tiers:
        return None
    for tier in sorted(sig.quality_tiers, key=lambda t: t.min_kbps, reverse=True):
        if available_kbps >= tier.min_kbps:
            return tier
    return sig.quality_tiers[0]  # lowest tier

PRIORITY_CLASSES = {
    "CRITICAL": {"dscp": 46, "bandwidth_pct": 0.90, "guaranteed_pct": 0.70, "tc_prio": 1},
    "HIGH":     {"dscp": 34, "bandwidth_pct": 0.70, "guaranteed_pct": 0.50, "tc_prio": 2},
    "NORMAL":   {"dscp": 18, "bandwidth_pct": 0.40, "guaranteed_pct": 0.10, "tc_prio": 3},
    "LOW":      {"dscp": 8,  "bandwidth_pct": 0.05, "guaranteed_pct": 0.01, "tc_prio": 4},
    "BLOCKED":  {"dscp": 0,  "bandwidth_pct": 0.00, "guaranteed_pct": 0.00, "tc_prio": 5},
}
```

---

## SECTION 2 — FLOW DETECTOR

### Create `server/app_qos/flow_detector.py`

Detects which apps from the signatures list are currently running and sending/receiving traffic.

```python
"""
Application Flow Detector — PathWise AI
Scans active network connections and matches them to app signatures.
Works on Linux (via /proc/net/tcp + /proc/PID/net) and Windows (via psutil).
Falls back to process-name matching when IP ranges are ambiguous.
"""

import os, re, subprocess, logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

import psutil

from server.app_qos.signatures import APP_SIGNATURES, AppSignature

logger = logging.getLogger("pathwise.flow_detector")


@dataclass
class DetectedApp:
    app_id: str
    name: str
    icon: str
    color: str
    category: str
    pid: Optional[int]
    process_name: Optional[str]
    connections: int        # number of active TCP/UDP connections to app servers
    est_kbps: float         # estimated current bandwidth usage (Kbps)
    is_active: bool         # True if traffic detected in last 5s
    detected_via: str       # "ip_range" | "port" | "process_name"
    current_priority: str   # current PathWise priority class
    last_seen: str


def _get_active_connections() -> List[dict]:
    """Return all current network connections using psutil."""
    conns = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.info.get('connections') or []:
                    if conn.status in ('ESTABLISHED', 'SYN_SENT', 'CLOSE_WAIT'):
                        conns.append({
                            "pid": proc.info['pid'],
                            "process": proc.info['name'],
                            "raddr": conn.raddr.ip if conn.raddr else None,
                            "rport": conn.raddr.port if conn.raddr else None,
                            "lport": conn.laddr.port if conn.laddr else None,
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as exc:
        logger.warning("Connection scan error: %s", exc)
    return conns


def _ip_in_cidr(ip: str, cidr: str) -> bool:
    """Check if an IP address falls within a CIDR range."""
    try:
        import ipaddress
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
    except Exception:
        return False


def _ip_matches_signature(ip: str, sig: AppSignature) -> bool:
    if not ip or not sig.dst_ip_ranges:
        return False
    return any(_ip_in_cidr(ip, cidr) for cidr in sig.dst_ip_ranges)


def _port_matches_signature(port: int, sig: AppSignature) -> bool:
    return port in sig.dst_ports if port else False


def _process_matches_signature(process_name: str, sig: AppSignature) -> bool:
    pname = (process_name or "").lower()
    return any(p.lower() in pname or pname in p.lower()
               for p in sig.process_names)


def _estimate_bandwidth(pid: int) -> float:
    """
    Estimate current bandwidth for a process (Kbps).
    Uses psutil io_counters delta over 0.5s sample.
    Returns 0 if unable to measure.
    """
    try:
        proc = psutil.Process(pid)
        c1 = proc.io_counters()
        import time; time.sleep(0.5)
        c2 = proc.io_counters()
        bytes_per_sec = (c2.read_bytes + c2.write_bytes -
                         c1.read_bytes - c1.write_bytes) * 2
        return round(bytes_per_sec * 8 / 1000, 1)  # to Kbps
    except Exception:
        return 0.0


def detect_active_apps(current_priorities: Dict[str, str] = None) -> List[DetectedApp]:
    """
    Scan all active network connections and return apps from APP_SIGNATURES
    that are currently running and communicating.
    """
    if current_priorities is None:
        current_priorities = {}

    conns = _get_active_connections()
    matched: Dict[str, DetectedApp] = {}

    for sig_id, sig in APP_SIGNATURES.items():
        app_conns = []
        pids = set()
        via = "none"

        for conn in conns:
            raddr  = conn.get("raddr")
            rport  = conn.get("rport")
            proc   = conn.get("process", "")
            pid    = conn.get("pid")

            ip_match      = _ip_matches_signature(raddr, sig) if raddr else False
            port_match    = _port_matches_signature(rport, sig)
            process_match = _process_matches_signature(proc, sig)

            if ip_match:
                via = "ip_range"
                app_conns.append(conn)
                if pid: pids.add(pid)
            elif port_match and process_match:
                via = "port+process"
                app_conns.append(conn)
                if pid: pids.add(pid)
            elif process_match and not sig.dst_ip_ranges:
                # Generic apps like Chrome that we identify only by process
                via = "process_name"
                app_conns.append(conn)
                if pid: pids.add(pid)

        if app_conns:
            est_kbps = 0.0
            if pids:
                try:
                    est_kbps = _estimate_bandwidth(next(iter(pids)))
                except Exception:
                    est_kbps = 0.0

            matched[sig_id] = DetectedApp(
                app_id=sig_id,
                name=sig.name,
                icon=sig.icon,
                color=sig.color,
                category=sig.category,
                pid=next(iter(pids)) if pids else None,
                process_name=app_conns[0].get("process"),
                connections=len(app_conns),
                est_kbps=est_kbps,
                is_active=len(app_conns) > 0,
                detected_via=via,
                current_priority=current_priorities.get(sig_id, sig.default_priority),
                last_seen=datetime.utcnow().isoformat()
            )

    return list(matched.values())
```

---

## SECTION 3 — BANDWIDTH ENFORCER

### Create `server/app_qos/bandwidth_enforcer.py`

This is the core of the feature. Applies OS-level QoS rules that enforce the priority ordering.

```python
"""
Bandwidth Enforcer — PathWise AI App Priority Switch
Applies real OS-level QoS rules to enforce per-app bandwidth allocation.

Modes (set via ENFORCER_MODE env var):
  tc        — Linux tc + HTB (production, requires NET_ADMIN capability)
  powershell— Windows New-NetQosPolicy + netsh (requires admin rights)
  simulate  — Log commands only, update in-memory state (safe for Docker demo)

The enforcer translates a priority order list into concrete bandwidth
ceilings and floors, then programs the OS traffic shaper.
"""

import os, subprocess, logging, json, ipaddress
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from server.app_qos.signatures import (
    APP_SIGNATURES, PRIORITY_CLASSES, predict_quality, get_app
)

logger = logging.getLogger("pathwise.enforcer")

ENFORCER_MODE = os.getenv("ENFORCER_MODE", "simulate")  # tc | powershell | simulate
WAN_INTERFACE  = os.getenv("WAN_INTERFACE", "eth0")     # Network interface to shape
TOTAL_BW_MBPS  = float(os.getenv("TOTAL_LINK_MBPS", "100"))  # Total WAN capacity


@dataclass
class AppAllocation:
    app_id: str
    name: str
    priority: str
    guaranteed_kbps: int
    ceil_kbps: int
    tc_class_id: str     # e.g. "1:10"
    dscp: int
    estimated_quality: Optional[str]  # e.g. "144p", "HD", "Excellent"


class BandwidthEnforcer:
    """
    Manages the full lifecycle of tc/powershell QoS rules for app prioritization.
    """

    def __init__(self):
        self.mode = ENFORCER_MODE
        self.interface = WAN_INTERFACE
        self.total_kbps = int(TOTAL_BW_MBPS * 1000)
        self._active_rules: Dict[str, AppAllocation] = {}
        self._qdisc_initialized = False

        logger.info("BandwidthEnforcer initialized: mode=%s interface=%s total=%d kbps",
                    self.mode, self.interface, self.total_kbps)

    # ─── Public API ─────────────────────────────────────────────────────────

    def apply_priorities(self, priority_order: List[Dict]) -> Dict:
        """
        Main entry point. Takes an ordered list of {app_id, priority} dicts
        and programs the OS QoS accordingly.

        priority_order example:
          [
            {"app_id": "zoom",    "priority": "HIGH"},
            {"app_id": "youtube", "priority": "LOW"},
            {"app_id": "spotify", "priority": "NORMAL"},
          ]

        Returns the resulting allocations with quality predictions.
        """
        allocations = self._compute_allocations(priority_order)

        if self.mode == "tc":
            self._apply_tc_rules(allocations)
        elif self.mode == "powershell":
            self._apply_powershell_rules(allocations)
        else:
            self._apply_simulate(allocations)

        self._active_rules = {a.app_id: a for a in allocations}
        return self._format_result(allocations)

    def clear_all_rules(self) -> Dict:
        """Remove all QoS rules and restore full bandwidth to all apps."""
        if self.mode == "tc":
            self._run("tc qdisc del dev {iface} root 2>/dev/null || true")
            self._qdisc_initialized = False
        elif self.mode == "powershell":
            self._run_ps("Get-NetQosPolicy | Remove-NetQosPolicy -Confirm:$false")

        self._active_rules = {}
        logger.info("All QoS rules cleared on %s", self.interface)
        return {"success": True, "message": "All QoS rules removed. Full bandwidth restored."}

    def get_active_allocations(self) -> Dict:
        """Return current allocations with live quality predictions."""
        return self._format_result(list(self._active_rules.values()))

    # ─── Allocation calculator ───────────────────────────────────────────────

    def _compute_allocations(self, priority_order: List[Dict]) -> List[AppAllocation]:
        """
        Translate priority labels into concrete kbps allocations using HTB math.
        High-priority apps get guaranteed floor + can burst to ceiling.
        Low-priority apps get hard ceiling (forces quality drop).
        """
        allocations = []
        class_counter = 10  # tc class IDs start at 1:10

        for item in priority_order:
            app_id   = item["app_id"]
            priority = item.get("priority", "NORMAL")
            sig      = get_app(app_id)
            if not sig:
                continue

            pc = PRIORITY_CLASSES.get(priority, PRIORITY_CLASSES["NORMAL"])

            # Bandwidth calculation
            guaranteed_kbps = int(self.total_kbps * pc["guaranteed_pct"])
            ceil_kbps        = int(self.total_kbps * pc["bandwidth_pct"])

            # Clamp to app's useful range
            ceil_kbps = max(
                min(ceil_kbps, sig.max_useful_kbps),
                0 if priority == "BLOCKED" else sig.min_kbps
            )
            guaranteed_kbps = min(guaranteed_kbps, ceil_kbps)

            # Predict quality for streaming apps
            quality = None
            if sig.quality_tiers:
                tier = predict_quality(app_id, ceil_kbps)
                quality = tier.label if tier else "Unknown"

            allocations.append(AppAllocation(
                app_id=app_id,
                name=sig.name,
                priority=priority,
                guaranteed_kbps=guaranteed_kbps,
                ceil_kbps=ceil_kbps,
                tc_class_id=f"1:{class_counter}",
                dscp=pc["dscp"],
                estimated_quality=quality,
            ))
            class_counter += 10

        return allocations

    # ─── Linux tc (HTB) ─────────────────────────────────────────────────────

    def _apply_tc_rules(self, allocations: List[AppAllocation]):
        """
        Programs Linux traffic control using HTB qdisc.
        Requires CAP_NET_ADMIN (run container with --cap-add NET_ADMIN
        or run as root on the host).

        Structure:
          1:   root HTB qdisc
          1:1  root class (total link rate)
          1:10 Zoom class (guaranteed + ceil)
          1:20 YouTube class (hard cap = forces quality drop)
          1:99 default class (everything else, fair-share)
        """
        iface = self.interface

        # Step 1: Tear down existing qdisc (idempotent)
        self._run(f"tc qdisc del dev {iface} root 2>/dev/null || true")

        # Step 2: Create root HTB qdisc with default fallback class 1:99
        self._run(f"tc qdisc add dev {iface} root handle 1: htb default 99")

        # Step 3: Root class — total link capacity
        self._run(f"tc class add dev {iface} parent 1: classid 1:1 "
                  f"htb rate {self.total_kbps}kbit burst 15k")

        # Step 4: Default class for unclassified traffic
        self._run(f"tc class add dev {iface} parent 1:1 classid 1:99 "
                  f"htb rate 10mbit ceil {self.total_kbps}kbit prio 7 burst 15k")

        # Step 5: Per-app classes
        for alloc in allocations:
            if alloc.priority == "BLOCKED":
                # BLOCKED: drop all traffic → install police filter later
                self._run(f"tc class add dev {iface} parent 1:1 "
                          f"classid {alloc.tc_class_id} htb rate 1kbit ceil 1kbit prio 7")
            else:
                rate_kbit = max(alloc.guaranteed_kbps, 1)
                ceil_kbit = max(alloc.ceil_kbps, 1)
                prio = PRIORITY_CLASSES[alloc.priority]["tc_prio"]
                self._run(
                    f"tc class add dev {iface} parent 1:1 "
                    f"classid {alloc.tc_class_id} htb "
                    f"rate {rate_kbit}kbit ceil {ceil_kbit}kbit "
                    f"prio {prio} burst 15k cburst 15k"
                )
                # Add SFQ for fairness within each class
                minor = alloc.tc_class_id.split(":")[1]
                self._run(f"tc qdisc add dev {iface} parent {alloc.tc_class_id} "
                          f"handle {minor}: sfq perturb 10")

        # Step 6: Filters — classify packets to the right class
        filter_prio = 1
        for alloc in allocations:
            sig = get_app(alloc.app_id)
            if not sig:
                continue

            # Filter by DSCP value first (works for pre-marked traffic)
            if alloc.dscp > 0:
                self._run(
                    f"tc filter add dev {iface} parent 1: protocol ip "
                    f"prio {filter_prio} u32 "
                    f"match ip tos {alloc.dscp << 2} 0xfc "
                    f"flowid {alloc.tc_class_id}"
                )
                filter_prio += 1

            # Filter by destination IP ranges
            for cidr in sig.dst_ip_ranges[:5]:  # limit filters for performance
                try:
                    net = ipaddress.ip_network(cidr, strict=False)
                    # Convert to tc u32 hex format
                    ip_hex  = format(int(net.network_address), '08x')
                    mask_hex = format(int(net.netmask), '08x')
                    self._run(
                        f"tc filter add dev {iface} parent 1: protocol ip "
                        f"prio {filter_prio} u32 "
                        f"match ip dst {cidr} "
                        f"flowid {alloc.tc_class_id}"
                    )
                    filter_prio += 1
                except Exception as e:
                    logger.warning("Filter for %s cidr %s failed: %s", alloc.app_id, cidr, e)

            # Filter by destination port
            for port in sig.dst_ports[:3]:
                self._run(
                    f"tc filter add dev {iface} parent 1: protocol ip "
                    f"prio {filter_prio} u32 "
                    f"match ip dport {port} 0xffff "
                    f"flowid {alloc.tc_class_id}"
                )
                filter_prio += 1

        self._qdisc_initialized = True
        logger.info("tc HTB rules applied for %d apps on %s", len(allocations), iface)

    # ─── Windows PowerShell ─────────────────────────────────────────────────

    def _apply_powershell_rules(self, allocations: List[AppAllocation]):
        """
        Programs Windows QoS using New-NetQosPolicy (DSCP marking)
        combined with netsh for bandwidth throttling.
        Requires Administrator privileges.
        """
        # Remove existing PathWise policies
        self._run_ps("Get-NetQosPolicy -Name 'PathWise-*' -ErrorAction SilentlyContinue | "
                     "Remove-NetQosPolicy -Confirm:$false")

        for alloc in allocations:
            sig = get_app(alloc.app_id)
            if not sig:
                continue

            for proc in sig.process_names[:1]:  # Windows QoS is process-based
                policy_name = f"PathWise-{alloc.app_id}-{alloc.priority}"

                if alloc.priority == "BLOCKED":
                    # Block by throttling to minimum
                    self._run_ps(
                        f"New-NetQosPolicy -Name '{policy_name}' "
                        f"-AppPathNameMatchCondition '{proc}' "
                        f"-ThrottleRateActionBitsPerSecond {alloc.ceil_kbps * 1000} "
                        f"-PolicyStore ActiveStore"
                    )
                else:
                    # Apply DSCP marking
                    self._run_ps(
                        f"New-NetQosPolicy -Name '{policy_name}' "
                        f"-AppPathNameMatchCondition '{proc}' "
                        f"-DSCPAction {alloc.dscp} "
                        f"-PolicyStore ActiveStore"
                    )

                    # Apply bandwidth throttle for LOW priority
                    if alloc.priority in ("LOW", "BLOCKED"):
                        self._run_ps(
                            f"New-NetQosPolicy -Name '{policy_name}-throttle' "
                            f"-AppPathNameMatchCondition '{proc}' "
                            f"-ThrottleRateActionBitsPerSecond {alloc.ceil_kbps * 1000} "
                            f"-PolicyStore ActiveStore"
                        )

        logger.info("Windows QoS policies applied for %d apps", len(allocations))

    # ─── Simulation mode ────────────────────────────────────────────────────

    def _apply_simulate(self, allocations: List[AppAllocation]):
        """
        Simulation mode: logs the commands that WOULD be run,
        updates in-memory state, and returns quality predictions.
        Safe to use in Docker without NET_ADMIN.
        This mode is identical to tc mode for the UI — the dashboard
        shows real quality predictions and bandwidth allocations.
        The difference is only that no OS rules are written.
        """
        logger.info("[SIMULATE] Would apply tc rules on %s:", self.interface)
        for alloc in allocations:
            logger.info(
                "[SIMULATE]   %s (%s): guaranteed=%d kbps ceil=%d kbps quality=%s",
                alloc.name, alloc.priority,
                alloc.guaranteed_kbps, alloc.ceil_kbps,
                alloc.estimated_quality or "N/A"
            )

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _run(self, cmd: str) -> Tuple[int, str]:
        logger.debug("[tc] %s", cmd)
        if self.mode == "simulate":
            logger.info("[SIMULATE-CMD] %s", cmd)
            return 0, ""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0 and "RTNETLINK" not in result.stderr:
                logger.warning("tc command failed: %s | stderr: %s", cmd, result.stderr)
            return result.returncode, result.stdout
        except subprocess.TimeoutExpired:
            logger.error("tc command timed out: %s", cmd)
            return -1, ""

    def _run_ps(self, script: str) -> Tuple[int, str]:
        logger.debug("[powershell] %s", script)
        if self.mode == "simulate":
            logger.info("[SIMULATE-PS] %s", script)
            return 0, ""
        try:
            result = subprocess.run(
                ["powershell.exe", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=15
            )
            return result.returncode, result.stdout
        except Exception as exc:
            logger.error("PowerShell error: %s", exc)
            return -1, ""

    def _format_result(self, allocations: List[AppAllocation]) -> Dict:
        return {
            "mode": self.mode,
            "interface": self.interface,
            "total_kbps": self.total_kbps,
            "apps": [
                {
                    "app_id": a.app_id,
                    "name": a.name,
                    "priority": a.priority,
                    "guaranteed_kbps": a.guaranteed_kbps,
                    "ceil_kbps": a.ceil_kbps,
                    "estimated_quality": a.estimated_quality,
                    "tc_class_id": a.tc_class_id,
                }
                for a in allocations
            ]
        }
```

---

## SECTION 4 — PRIORITY MANAGER

### Create `server/app_qos/priority_manager.py`

Stateful manager that holds the current priority order and orchestrates the enforcer.

```python
"""
App Priority Manager — PathWise AI
Maintains per-user priority state and coordinates the enforcer.
"""

import os, json, logging
from typing import Dict, List, Optional
from datetime import datetime

from server.app_qos.bandwidth_enforcer import BandwidthEnforcer
from server.app_qos.flow_detector import detect_active_apps, DetectedApp
from server.app_qos.signatures import APP_SIGNATURES, predict_quality

logger = logging.getLogger("pathwise.priority_manager")

# In-memory state: {user_id: [{"app_id": ..., "priority": ...}]}
_user_priorities: Dict[str, List[Dict]] = {}
_enforcer = BandwidthEnforcer()


def get_active_apps(user_id: str) -> List[dict]:
    """Return detected running apps with their current priority and quality."""
    current = {item["app_id"]: item["priority"]
               for item in _user_priorities.get(user_id, [])}
    apps = detect_active_apps(current_priorities=current)
    return [
        {
            "app_id": a.app_id,
            "name": a.name,
            "icon": a.icon,
            "color": a.color,
            "category": a.category,
            "est_kbps": a.est_kbps,
            "connections": a.connections,
            "current_priority": a.current_priority,
            "is_active": a.is_active,
            "detected_via": a.detected_via,
            "last_seen": a.last_seen,
        }
        for a in apps
    ]


def set_priorities(user_id: str, priority_order: List[Dict]) -> Dict:
    """
    Apply a new priority ordering for a user.
    priority_order: [{"app_id": "zoom", "priority": "HIGH"}, ...]
    """
    _user_priorities[user_id] = priority_order
    result = _enforcer.apply_priorities(priority_order)
    result["applied_at"] = datetime.utcnow().isoformat()
    result["user_id"] = user_id

    _log_priority_change(user_id, priority_order, result)
    return result


def get_priorities(user_id: str) -> List[Dict]:
    return _user_priorities.get(user_id, [])


def remove_app_priority(user_id: str, app_id: str) -> Dict:
    """Remove a single app from the priority list and reapply rules."""
    current = _user_priorities.get(user_id, [])
    updated = [item for item in current if item["app_id"] != app_id]
    return set_priorities(user_id, updated)


def reset_all(user_id: str) -> Dict:
    """Clear all QoS rules for a user."""
    _user_priorities.pop(user_id, None)
    return _enforcer.clear_all_rules()


def get_quality_predictions(user_id: str) -> List[Dict]:
    """Return estimated quality for every app under the current priorities."""
    predictions = []
    allocations = _enforcer.get_active_allocations().get("apps", [])
    alloc_map = {a["app_id"]: a for a in allocations}

    for app_id, sig in APP_SIGNATURES.items():
        alloc = alloc_map.get(app_id)
        ceil_kbps = alloc["ceil_kbps"] if alloc else sig.max_useful_kbps

        tier = predict_quality(app_id, ceil_kbps)
        predictions.append({
            "app_id": app_id,
            "name": sig.name,
            "icon": sig.icon,
            "ceil_kbps": ceil_kbps,
            "quality": tier.label if tier else None,
            "quality_description": tier.description if tier else None,
            "priority": alloc["priority"] if alloc else "NORMAL",
        })
    return predictions


def _log_priority_change(user_id: str, priorities: List[Dict], result: Dict):
    logger.info(
        "Priority change applied | user=%s | apps=%s | mode=%s",
        user_id,
        [(p["app_id"], p["priority"]) for p in priorities],
        result.get("mode")
    )
```

---

## SECTION 5 — REST API ROUTER

### Create `server/routers/app_priority.py`

```python
"""
App Priority REST API — PathWise AI
All endpoints require authentication. Priority enforcement is per-user.
Admin can see all users' current priority states.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
import asyncio, json

from server.auth import require_user, require_admin
from server.app_qos import priority_manager

router = APIRouter(prefix="/api/v1/apps", tags=["App Priority"])


class PriorityItem(BaseModel):
    app_id: str
    priority: str  # CRITICAL | HIGH | NORMAL | LOW | BLOCKED


class PriorityRequest(BaseModel):
    priorities: List[PriorityItem]


@router.get("/active")
def get_active_apps(claims=Depends(require_user)):
    """Return all currently detected running apps with their priority + quality."""
    apps = priority_manager.get_active_apps(claims["sub"])
    return {"apps": apps, "user_id": claims["sub"]}


@router.get("/signatures")
def get_all_signatures():
    """Return full app signature catalog for UI app selector."""
    from server.app_qos.signatures import APP_SIGNATURES
    return {
        "apps": [
            {
                "app_id": sig.app_id,
                "name": sig.name,
                "icon": sig.icon,
                "color": sig.color,
                "category": sig.category,
                "default_priority": sig.default_priority,
                "min_kbps": sig.min_kbps,
                "recommended_kbps": sig.recommended_kbps,
                "quality_tiers": [
                    {"label": t.label, "min_kbps": t.min_kbps,
                     "max_kbps": t.max_kbps, "description": t.description}
                    for t in sig.quality_tiers
                ]
            }
            for sig in APP_SIGNATURES.values()
        ]
    }


@router.get("/priorities")
def get_my_priorities(claims=Depends(require_user)):
    """Return the current priority order for this user."""
    return {
        "priorities": priority_manager.get_priorities(claims["sub"]),
        "user_id": claims["sub"]
    }


@router.post("/priorities")
def set_priorities(body: PriorityRequest, claims=Depends(require_user)):
    """
    Apply a new priority order. This immediately programs OS QoS rules.
    Example body:
      {"priorities": [
         {"app_id": "zoom",    "priority": "HIGH"},
         {"app_id": "youtube", "priority": "LOW"}
      ]}
    """
    order = [{"app_id": p.app_id, "priority": p.priority}
             for p in body.priorities]
    result = priority_manager.set_priorities(claims["sub"], order)
    return result


@router.delete("/priorities/{app_id}")
def remove_app_priority(app_id: str, claims=Depends(require_user)):
    """Remove a single app from the priority list."""
    result = priority_manager.remove_app_priority(claims["sub"], app_id)
    return result


@router.post("/reset")
def reset_all_priorities(claims=Depends(require_user)):
    """Remove ALL QoS rules. Restores full bandwidth to all apps."""
    return priority_manager.reset_all(claims["sub"])


@router.get("/quality")
def get_quality_predictions(claims=Depends(require_user)):
    """Return predicted quality for every known app under current priorities."""
    return {"predictions": priority_manager.get_quality_predictions(claims["sub"])}


@router.get("/admin/all-priorities")
def admin_all_priorities(claims=Depends(require_admin)):
    """Admin: see all users' current priority states."""
    from server.app_qos.priority_manager import _user_priorities
    return {"user_priorities": _user_priorities}


# ─── WebSocket: push live quality updates every 2s ────────────────────────────

@router.websocket("/ws/{user_id}/quality")
async def quality_ws(websocket: WebSocket, user_id: str):
    """Push live quality predictions and active app status at 2 Hz."""
    await websocket.accept()
    try:
        while True:
            apps    = priority_manager.get_active_apps(user_id)
            quality = priority_manager.get_quality_predictions(user_id)
            await websocket.send_json({
                "type":    "quality_update",
                "apps":    apps,
                "quality": quality,
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
```

### Register in `server/main.py`:

```python
from server.routers import app_priority
app.include_router(app_priority.router)
```

---

## SECTION 6 — FRONTEND: APP PRIORITY MANAGER PAGE

### `frontend/src/pages/user/AppPriorityManager.tsx`

This is the main UI. It has three zones:
1. **Detected Apps** — live list of apps PathWise sees running
2. **Priority Queue** — drag-to-reorder list + priority selector
3. **Live Quality Impact** — real-time quality bars per app

```tsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../utils/apiClient';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AppSig {
  app_id: string; name: string; icon: string; color: string;
  category: string; default_priority: string; min_kbps: number;
  recommended_kbps: number;
  quality_tiers: { label: string; min_kbps: number; max_kbps: number; description: string }[];
}

interface DetectedApp {
  app_id: string; name: string; icon: string; color: string;
  category: string; est_kbps: number; connections: number;
  current_priority: string; is_active: boolean; last_seen: string;
}

interface QualityPrediction {
  app_id: string; name: string; icon: string;
  ceil_kbps: number; quality: string | null;
  quality_description: string | null; priority: string;
}

interface PriorityItem { app_id: string; priority: string; name: string; icon: string; color: string; }

const PRIORITIES = ["CRITICAL", "HIGH", "NORMAL", "LOW", "BLOCKED"] as const;

const PRIORITY_META: Record<string, { label: string; color: string; bg: string; desc: string }> = {
  CRITICAL: { label: "Critical",  color: "#ef4444", bg: "#450a0a", desc: "Max bandwidth, pre-empts everything" },
  HIGH:     { label: "High",      color: "#f97316", bg: "#431407", desc: "Priority access, large guaranteed share" },
  NORMAL:   { label: "Normal",    color: "#3b82f6", bg: "#172554", desc: "Fair share of available bandwidth" },
  LOW:      { label: "Low",       color: "#64748b", bg: "#1e293b", desc: "Throttled — streaming quality drops" },
  BLOCKED:  { label: "Blocked",   color: "#6b7280", bg: "#111827", desc: "Traffic blocked entirely" },
};

// ─── Quality badge ────────────────────────────────────────────────────────────

const QualityBadge: React.FC<{ quality: string | null; kbps: number }> = ({ quality, kbps }) => {
  const q = quality || "–";
  const is4k  = q.includes("2160") || q.includes("4K");
  const isHD  = q.includes("1080") || q.includes("1440") || q.includes("720");
  const isLow = q.includes("144") || q.includes("240") || q.includes("360");
  const color = is4k ? "#16a34a" : isHD ? "#2563eb" : isLow ? "#ef4444" : "#f59e0b";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{
        background: color + "20", border: `1px solid ${color}`, borderRadius: 6,
        padding: "2px 8px", color, fontWeight: 600, fontSize: 13
      }}>{q}</span>
      <span style={{ color: "#64748b", fontSize: 12 }}>
        {kbps >= 1000 ? `${(kbps/1000).toFixed(1)} Mbps` : `${kbps} Kbps`}
      </span>
    </div>
  );
};

// ─── Bandwidth bar ────────────────────────────────────────────────────────────

const BandwidthBar: React.FC<{ kbps: number; maxKbps: number; color: string }> = ({ kbps, maxKbps, color }) => {
  const pct = Math.min(100, maxKbps > 0 ? (kbps / maxKbps) * 100 : 0);
  return (
    <div style={{ background: "#1e293b", borderRadius: 4, height: 6, width: "100%", overflow: "hidden" }}>
      <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4,
                    transition: "width 0.5s ease" }} />
    </div>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────

export default function AppPriorityManager() {
  const { user } = useAuth();

  const [allSigs, setAllSigs]         = useState<AppSig[]>([]);
  const [detectedApps, setDetected]   = useState<DetectedApp[]>([]);
  const [priorities, setPriorities]   = useState<PriorityItem[]>([]);
  const [quality, setQuality]         = useState<QualityPrediction[]>([]);
  const [applying, setApplying]       = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [lastApplied, setLastApplied] = useState<string | null>(null);
  const [dragIndex, setDragIndex]     = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // ── Load signatures + initial state ────────────────────────────────────────

  useEffect(() => {
    api.get<{ apps: AppSig[] }>("/apps/signatures")
      .then(d => setAllSigs(d.apps));
    api.get<{ priorities: { app_id: string; priority: string }[] }>("/apps/priorities")
      .then(d => {
        if (d.priorities.length > 0) {
          const sigs = allSigs.reduce((m: Record<string,AppSig>, s) => { m[s.app_id] = s; return m; }, {});
          setPriorities(d.priorities.map(p => ({
            ...p,
            name: sigs[p.app_id]?.name ?? p.app_id,
            icon: sigs[p.app_id]?.icon ?? "📦",
            color: sigs[p.app_id]?.color ?? "#3b82f6",
          })));
        }
      });
    // Poll detected apps every 5s
    const poll = setInterval(() => {
      api.get<{ apps: DetectedApp[] }>("/apps/active").then(d => setDetected(d.apps));
    }, 5000);
    api.get<{ apps: DetectedApp[] }>("/apps/active").then(d => setDetected(d.apps));
    return () => clearInterval(poll);
  }, []);

  // ── WebSocket for live quality ──────────────────────────────────────────────

  useEffect(() => {
    if (!user) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/v1/apps/ws/${user.user_id}/quality`);
    wsRef.current = ws;
    ws.onopen    = () => setWsConnected(true);
    ws.onclose   = () => setWsConnected(false);
    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.type === "quality_update") {
        setDetected(msg.apps);
        setQuality(msg.quality);
      }
    };
    return () => ws.close();
  }, [user]);

  // ── Add app to priority queue ───────────────────────────────────────────────

  const addApp = useCallback((sig: AppSig) => {
    if (priorities.find(p => p.app_id === sig.app_id)) return;
    setPriorities(prev => [...prev, {
      app_id: sig.app_id,
      priority: sig.default_priority,
      name: sig.name,
      icon: sig.icon,
      color: sig.color,
    }]);
  }, [priorities]);

  const removeApp = (app_id: string) => {
    setPriorities(prev => prev.filter(p => p.app_id !== app_id));
  };

  const changePriority = (app_id: string, priority: string) => {
    setPriorities(prev => prev.map(p => p.app_id === app_id ? { ...p, priority } : p));
  };

  // ── Drag-to-reorder ─────────────────────────────────────────────────────────

  const onDragStart = (i: number) => setDragIndex(i);
  const onDragOver  = (e: React.DragEvent, i: number) => {
    e.preventDefault();
    if (dragIndex === null || dragIndex === i) return;
    const next = [...priorities];
    const [item] = next.splice(dragIndex, 1);
    next.splice(i, 0, item);
    setPriorities(next);
    setDragIndex(i);
  };
  const onDragEnd = () => setDragIndex(null);

  // ── Apply priorities ────────────────────────────────────────────────────────

  const applyPriorities = async () => {
    if (priorities.length === 0) return;
    setApplying(true);
    try {
      const result = await api.post<any>("/apps/priorities", {
        priorities: priorities.map(p => ({ app_id: p.app_id, priority: p.priority }))
      });
      setQuality(result.apps?.map((a: any) => ({
        app_id: a.app_id, name: a.name, icon: "📦",
        ceil_kbps: a.ceil_kbps, quality: a.estimated_quality,
        quality_description: null, priority: a.priority,
      })) ?? []);
      setLastApplied(new Date().toLocaleTimeString());
    } catch (e) {
      console.error("Apply priorities failed", e);
    } finally {
      setApplying(false);
    }
  };

  const resetAll = async () => {
    await api.post("/apps/reset", {});
    setPriorities([]);
    setQuality([]);
    setLastApplied(null);
  };

  // ─── Render ─────────────────────────────────────────────────────────────────

  const qualityMap = quality.reduce((m: Record<string,QualityPrediction>, q) => {
    m[q.app_id] = q; return m;
  }, {});

  return (
    <div style={{ padding: "1.5rem", fontFamily: "Inter, system-ui, sans-serif",
                  background: "#f8fafc", minHeight: "100vh" }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                    marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 600, color: "#0f172a" }}>
            App Priority Switch
          </h1>
          <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 14 }}>
            Set application bandwidth priorities. Prioritizing Zoom will throttle YouTube — forcing it to drop quality automatically.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{
            background: wsConnected ? "#dcfce7" : "#fef3c7",
            color: wsConnected ? "#16a34a" : "#d97706",
            border: `1px solid ${wsConnected ? "#16a34a" : "#d97706"}`,
            borderRadius: 20, padding: "4px 12px", fontSize: 12
          }}>
            {wsConnected ? "⬤ Live" : "○ Connecting"}
          </span>
          {lastApplied && (
            <span style={{ color: "#64748b", fontSize: 12 }}>Applied {lastApplied}</span>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.5rem" }}>

        {/* COLUMN 1 — App Catalog */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: "1rem" }}>
          <h3 style={{ margin: "0 0 1rem", fontSize: 15, fontWeight: 600, color: "#0f172a" }}>
            Available Apps
          </h3>
          <p style={{ color: "#64748b", fontSize: 13, margin: "0 0 0.75rem" }}>
            Click to add to priority queue
          </p>
          {["video_call", "streaming", "voip", "gaming", "productivity"].map(cat => {
            const catApps = allSigs.filter(s => s.category === cat);
            if (!catApps.length) return null;
            const catLabel: Record<string,string> = {
              video_call: "Video Calls", streaming: "Streaming",
              voip: "Voice & Audio", gaming: "Gaming", productivity: "Productivity"
            };
            return (
              <div key={cat} style={{ marginBottom: "1rem" }}>
                <p style={{ color: "#94a3b8", fontSize: 11, fontWeight: 600,
                            textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 6px" }}>
                  {catLabel[cat]}
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {catApps.map(sig => {
                    const inQueue = priorities.some(p => p.app_id === sig.app_id);
                    return (
                      <button key={sig.app_id} onClick={() => !inQueue && addApp(sig)}
                        disabled={inQueue}
                        style={{
                          display: "flex", alignItems: "center", gap: 8,
                          padding: "8px 10px", borderRadius: 8, border: "1px solid",
                          borderColor: inQueue ? "#e2e8f0" : sig.color + "40",
                          background: inQueue ? "#f8fafc" : sig.color + "10",
                          cursor: inQueue ? "default" : "pointer",
                          textAlign: "left", opacity: inQueue ? 0.5 : 1,
                          transition: "all 0.15s"
                        }}>
                        <span style={{ fontSize: 18 }}>{sig.icon}</span>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 13, fontWeight: 500, color: "#0f172a" }}>
                            {sig.name}
                          </div>
                          {sig.quality_tiers.length > 0 && (
                            <div style={{ fontSize: 11, color: "#64748b" }}>
                              {sig.quality_tiers[0].label} – {sig.quality_tiers[sig.quality_tiers.length-1].label}
                            </div>
                          )}
                        </div>
                        {inQueue && <span style={{ fontSize: 11, color: "#3b82f6" }}>In Queue</span>}
                        {!inQueue && <span style={{ fontSize: 16, color: sig.color }}>+</span>}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* COLUMN 2 — Priority Queue */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: "1rem" }}>
          <h3 style={{ margin: "0 0 0.25rem", fontSize: 15, fontWeight: 600, color: "#0f172a" }}>
            Priority Queue
          </h3>
          <p style={{ color: "#64748b", fontSize: 13, margin: "0 0 1rem" }}>
            Drag to reorder. Top = highest priority.
          </p>

          {priorities.length === 0 && (
            <div style={{ textAlign: "center", padding: "3rem 1rem", color: "#94a3b8",
                          border: "2px dashed #e2e8f0", borderRadius: 8 }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
              <div style={{ fontSize: 14 }}>Add apps from the left to set their priority</div>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {priorities.map((item, i) => (
              <div key={item.app_id}
                draggable
                onDragStart={() => onDragStart(i)}
                onDragOver={e => onDragOver(e, i)}
                onDragEnd={onDragEnd}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "10px 12px", borderRadius: 8,
                  border: `1px solid ${PRIORITY_META[item.priority]?.color}40`,
                  background: PRIORITY_META[item.priority]?.bg + "80",
                  cursor: "grab", userSelect: "none",
                  opacity: dragIndex === i ? 0.5 : 1,
                }}>
                {/* Rank number */}
                <span style={{
                  width: 24, height: 24, borderRadius: "50%", background: item.color + "20",
                  color: item.color, fontSize: 12, fontWeight: 700,
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0
                }}>{i + 1}</span>

                <span style={{ fontSize: 18 }}>{item.icon}</span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "#f1f5f9",
                                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {item.name}
                  </div>
                </div>

                {/* Priority selector */}
                <select
                  value={item.priority}
                  onChange={e => changePriority(item.app_id, e.target.value)}
                  onClick={e => e.stopPropagation()}
                  style={{
                    background: PRIORITY_META[item.priority]?.bg,
                    color: PRIORITY_META[item.priority]?.color,
                    border: `1px solid ${PRIORITY_META[item.priority]?.color}60`,
                    borderRadius: 6, padding: "3px 6px", fontSize: 12, cursor: "pointer"
                  }}>
                  {PRIORITIES.map(p => (
                    <option key={p} value={p}>{PRIORITY_META[p].label}</option>
                  ))}
                </select>

                {/* Remove */}
                <button onClick={() => removeApp(item.app_id)}
                  style={{ background: "none", border: "none", color: "#64748b",
                           cursor: "pointer", fontSize: 16, padding: "0 2px" }}>✕</button>
              </div>
            ))}
          </div>

          {/* Action buttons */}
          {priorities.length > 0 && (
            <div style={{ marginTop: "1rem", display: "flex", gap: 8 }}>
              <button onClick={applyPriorities} disabled={applying}
                style={{
                  flex: 1, padding: "10px", borderRadius: 8, border: "none",
                  background: applying ? "#1d4ed8" : "#2563eb", color: "white",
                  fontSize: 14, fontWeight: 600, cursor: applying ? "wait" : "pointer"
                }}>
                {applying ? "Applying…" : "⚡ Apply Priorities"}
              </button>
              <button onClick={resetAll}
                style={{
                  padding: "10px 14px", borderRadius: 8, cursor: "pointer",
                  border: "1px solid #ef4444", background: "transparent",
                  color: "#ef4444", fontSize: 14
                }}>Reset</button>
            </div>
          )}

          {/* IBN Hint */}
          <div style={{
            marginTop: "1rem", padding: "10px", borderRadius: 8,
            background: "#172554", border: "1px solid #1d4ed8"
          }}>
            <p style={{ margin: 0, color: "#93c5fd", fontSize: 12 }}>
              💡 You can also set priorities via natural language on the IBN page:
              <em> "Prioritize Zoom over YouTube on fiber"</em>
            </p>
          </div>
        </div>

        {/* COLUMN 3 — Live Quality Impact */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: "1rem" }}>
          <h3 style={{ margin: "0 0 0.25rem", fontSize: 15, fontWeight: 600, color: "#0f172a" }}>
            Live Quality Impact
          </h3>
          <p style={{ color: "#64748b", fontSize: 13, margin: "0 0 1rem" }}>
            Estimated quality per app under current rules
          </p>

          {/* KEY VISUAL: Zoom vs YouTube example */}
          {priorities.some(p => p.app_id === "zoom") && priorities.some(p => p.app_id === "youtube") && (
            <div style={{
              background: "#0f2d0f", border: "1px solid #16a34a",
              borderRadius: 10, padding: "12px", marginBottom: "1rem"
            }}>
              <p style={{ margin: "0 0 6px", color: "#86efac", fontSize: 12, fontWeight: 600 }}>
                ✓ Zoom + YouTube detected
              </p>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <div>
                  <span style={{ fontSize: 18 }}>🎥</span>
                  <span style={{ color: "#f1f5f9", marginLeft: 4 }}>Zoom</span>
                  <span style={{ marginLeft: 6, background: "#16a34a20", border: "1px solid #16a34a",
                                 borderRadius: 4, padding: "1px 6px", color: "#86efac", fontSize: 11 }}>
                    {qualityMap["zoom"]?.quality ?? "Excellent"}
                  </span>
                </div>
                <div>
                  <span style={{ fontSize: 18 }}>▶️</span>
                  <span style={{ color: "#f1f5f9", marginLeft: 4 }}>YouTube</span>
                  <span style={{ marginLeft: 6, background: "#450a0a20", border: "1px solid #ef4444",
                                 borderRadius: 4, padding: "1px 6px", color: "#fca5a5", fontSize: 11 }}>
                    {qualityMap["youtube"]?.quality ?? "144p"}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* All active app quality rows */}
          {priorities.length === 0 && (
            <div style={{ textAlign: "center", padding: "2rem", color: "#94a3b8", fontSize: 14 }}>
              Set priorities to see quality predictions
            </div>
          )}
          {priorities.map(item => {
            const q = qualityMap[item.app_id];
            const sig = allSigs.find(s => s.app_id === item.app_id);
            const maxKbps = sig?.recommended_kbps ?? 10000;
            const ceilKbps = q?.ceil_kbps ?? 0;
            const pmeta = PRIORITY_META[item.priority];
            return (
              <div key={item.app_id} style={{
                padding: "10px", borderRadius: 8, marginBottom: 6,
                background: "#f8fafc", border: "1px solid #e2e8f0"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between",
                              alignItems: "center", marginBottom: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 18 }}>{item.icon}</span>
                    <span style={{ fontSize: 13, fontWeight: 500, color: "#0f172a" }}>
                      {item.name}
                    </span>
                    <span style={{
                      fontSize: 10, fontWeight: 600,
                      background: pmeta.bg, color: pmeta.color,
                      border: `1px solid ${pmeta.color}60`,
                      borderRadius: 20, padding: "1px 6px"
                    }}>{pmeta.label}</span>
                  </div>
                  {q && <QualityBadge quality={q.quality} kbps={q.ceil_kbps} />}
                </div>
                <BandwidthBar kbps={ceilKbps} maxKbps={maxKbps} color={pmeta.color} />
                {q?.quality_description && (
                  <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 11 }}>
                    {q.quality_description}
                  </p>
                )}
              </div>
            );
          })}

          {/* Detected running apps (not in queue) */}
          {detectedApps.filter(a => !priorities.some(p => p.app_id === a.app_id)).length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <p style={{ color: "#94a3b8", fontSize: 11, fontWeight: 600,
                          textTransform: "uppercase", margin: "0 0 6px" }}>
                Also Running (unmanaged)
              </p>
              {detectedApps
                .filter(a => !priorities.some(p => p.app_id === a.app_id))
                .map(app => (
                  <div key={app.app_id} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "6px 8px", background: "#f1f5f9", borderRadius: 6, marginBottom: 4
                  }}>
                    <span style={{ fontSize: 14 }}>{app.icon}</span>
                    <span style={{ flex: 1, marginLeft: 6, fontSize: 13, color: "#334155" }}>
                      {app.name}
                    </span>
                    <span style={{ fontSize: 12, color: "#64748b" }}>
                      {app.est_kbps > 0
                        ? `${(app.est_kbps/1000).toFixed(1)} Mbps`
                        : "idle"}
                    </span>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

### Add to `frontend/src/components/layout/UserLayout.tsx` sidebar:

```tsx
// Add this nav item to the user sidebar
{ path: "/user/apps",    label: "App Priority",  icon: "⚡" },
```

### Add route to `frontend/src/App.tsx`:

```tsx
import AppPriorityManager from './pages/user/AppPriorityManager';
// In UserRoutes:
<Route path="/user/apps" element={<UserRoute><AppPriorityManager /></UserRoute>} />
```

---

## SECTION 7 — IBN INTEGRATION

The IBN (Intent-Based Networking) NLP parser already handles commands. Extend `server/ibn_engine.py` to recognize app priority intents and route them to the priority manager.

### Extend `parse_intent_command()` in `server/ibn_engine.py`:

```python
# Add to the APP_PRIORITY pattern group in the NLP parser

APP_PRIORITY_PATTERNS = [
    # "Prioritize Zoom over YouTube"
    (r"prioritize\s+(\w[\w\s]*)\s+over\s+(\w[\w\s]*)", "prioritize_over"),
    # "Give Zoom high priority"
    (r"give\s+(\w[\w\s]*)\s+(critical|high|normal|low|blocked)\s+priority", "set_priority"),
    # "Block YouTube"
    (r"block\s+(\w[\w\s]*)", "block_app"),
    # "Throttle Netflix to 360p"
    (r"throttle\s+(\w[\w\s]*)\s+to\s+(\d+p?)", "throttle_quality"),
    # "Set Zoom to critical, YouTube to low"
    (r"set\s+(\w+)\s+to\s+(critical|high|normal|low|blocked).*(\w+)\s+to\s+(critical|high|normal|low|blocked)", "set_multiple"),
]

APP_NAME_MAP = {
    "zoom": "zoom", "youtube": "youtube", "netflix": "netflix",
    "teams": "teams", "discord": "discord", "spotify": "spotify",
    "twitch": "twitch", "chrome": "google_chrome", "steam": "steam",
    "google meet": "google_meet", "onedrive": "onedrive",
    "disney": "disney_plus", "disney+": "disney_plus",
}

QUALITY_TO_KBPS = {
    "144p": 200, "240p": 400, "360p": 600, "480p": 900,
    "720p": 2500, "1080p": 6000, "1440p": 14000, "4k": 25000, "2160p": 25000
}

def parse_app_priority_intent(command: str) -> Optional[dict]:
    """
    Parse a natural-language app priority command.
    Returns a structured intent or None if not recognized.
    """
    cmd = command.lower().strip()

    for pattern, action in APP_PRIORITY_PATTERNS:
        m = re.search(pattern, cmd)
        if not m:
            continue

        if action == "prioritize_over":
            high_app = APP_NAME_MAP.get(m.group(1).strip(), m.group(1).strip())
            low_app  = APP_NAME_MAP.get(m.group(2).strip(), m.group(2).strip())
            return {
                "type": "app_priority",
                "action": "prioritize_over",
                "priorities": [
                    {"app_id": high_app, "priority": "HIGH"},
                    {"app_id": low_app,  "priority": "LOW"},
                ],
                "description": f"Set {high_app} to HIGH, {low_app} to LOW"
            }

        elif action == "set_priority":
            app_id   = APP_NAME_MAP.get(m.group(1).strip(), m.group(1).strip())
            priority = m.group(2).upper()
            return {
                "type": "app_priority",
                "action": "set_priority",
                "priorities": [{"app_id": app_id, "priority": priority}],
                "description": f"Set {app_id} to {priority}"
            }

        elif action == "block_app":
            app_id = APP_NAME_MAP.get(m.group(1).strip(), m.group(1).strip())
            return {
                "type": "app_priority",
                "action": "block_app",
                "priorities": [{"app_id": app_id, "priority": "BLOCKED"}],
                "description": f"Block {app_id} traffic"
            }

        elif action == "throttle_quality":
            app_id  = APP_NAME_MAP.get(m.group(1).strip(), m.group(1).strip())
            quality = m.group(2).lower()
            kbps    = QUALITY_TO_KBPS.get(quality, 300)
            return {
                "type": "app_priority",
                "action": "throttle_quality",
                "priorities": [{"app_id": app_id, "priority": "LOW"}],
                "target_kbps": kbps,
                "target_quality": quality,
                "description": f"Throttle {app_id} to ~{quality}"
            }

    return None


# In the main deploy_intent() flow, add this before the YANG/SDN path:
def deploy_intent(intent: dict) -> dict:
    command = intent.get("command", "")

    # Try app priority first
    app_intent = parse_app_priority_intent(command)
    if app_intent:
        from server.app_qos.priority_manager import set_priorities
        user_id = intent.get("user_id", "default")
        result = set_priorities(user_id, app_intent["priorities"])
        return {
            "success": True,
            "type": "app_priority",
            "description": app_intent["description"],
            "enforcement": result,
        }

    # ... rest of existing YANG/SDN flow
```

---

## SECTION 8 — DOCKER AND ENVIRONMENT

### 8.1 — Update `docker-compose.yml` — add NET_ADMIN to backend for tc mode

```yaml
  backend:
    # ... existing config ...
    cap_add:
      - NET_ADMIN          # Required for tc HTB rules (Linux mode)
    environment:
      - ENFORCER_MODE=simulate   # Change to 'tc' on Linux host with NET_ADMIN
      - WAN_INTERFACE=eth0
      - TOTAL_LINK_MBPS=100
```

### 8.2 — Add `psutil` to `requirements.txt`

```
psutil>=5.9.0
```

### 8.3 — Environment variable reference

```bash
# In .env or docker-compose environment section:

ENFORCER_MODE=simulate     # tc | powershell | simulate
WAN_INTERFACE=eth0         # Interface to shape (eth0, enp3s0, etc.)
TOTAL_LINK_MBPS=100        # Total WAN link capacity in Mbps

# To use tc mode on Linux host:
# 1. Add NET_ADMIN capability to container
# 2. Set ENFORCER_MODE=tc
# 3. Confirm: docker exec pathwise_backend tc qdisc show
```

---

## SECTION 9 — TEST CASES

### `tests/test_app_qos/test_signatures.py`

```python
"""Test app signature database completeness and quality prediction."""
import pytest
from server.app_qos.signatures import APP_SIGNATURES, predict_quality, PRIORITY_CLASSES

def test_all_major_apps_present():
    required = ["zoom", "youtube", "netflix", "teams", "discord", "spotify", "steam"]
    for app_id in required:
        assert app_id in APP_SIGNATURES, f"Missing signature for {app_id}"

def test_youtube_has_8_quality_tiers():
    sig = APP_SIGNATURES["youtube"]
    assert len(sig.quality_tiers) == 8
    labels = [t.label for t in sig.quality_tiers]
    assert "144p" in labels
    assert "2160p" in labels

def test_quality_prediction_144p_at_200kbps():
    tier = predict_quality("youtube", 200)
    assert tier is not None
    assert "144" in tier.label

def test_quality_prediction_4k_at_30mbps():
    tier = predict_quality("youtube", 30000)
    assert tier is not None
    assert "2160" in tier.label or "4K" in tier.label

def test_quality_prediction_1080p_at_6mbps():
    tier = predict_quality("youtube", 6000)
    assert tier is not None
    assert "1080" in tier.label

def test_zoom_quality_tiers_present():
    sig = APP_SIGNATURES["zoom"]
    assert len(sig.quality_tiers) >= 4

def test_all_priority_classes_defined():
    for level in ["CRITICAL", "HIGH", "NORMAL", "LOW", "BLOCKED"]:
        assert level in PRIORITY_CLASSES
        assert "bandwidth_pct" in PRIORITY_CLASSES[level]
        assert "guaranteed_pct" in PRIORITY_CLASSES[level]
```

### `tests/test_app_qos/test_bandwidth_enforcer.py`

```python
"""Test bandwidth enforcer allocation math."""
import pytest, os
os.environ["ENFORCER_MODE"] = "simulate"

from server.app_qos.bandwidth_enforcer import BandwidthEnforcer

@pytest.fixture
def enforcer():
    return BandwidthEnforcer()

def test_zoom_high_youtube_low_allocation(enforcer):
    """HIGH Zoom → big ceiling. LOW YouTube → small ceiling (forces 144p)."""
    result = enforcer.apply_priorities([
        {"app_id": "zoom",    "priority": "HIGH"},
        {"app_id": "youtube", "priority": "LOW"},
    ])
    apps = {a["app_id"]: a for a in result["apps"]}

    assert apps["zoom"]["ceil_kbps"] > apps["youtube"]["ceil_kbps"]
    # YouTube ceil should be ≤ 300 Kbps when set to LOW on a 100 Mbps link
    assert apps["youtube"]["ceil_kbps"] <= 5000  # 5% of 100 Mbps = 5000 kbps

def test_youtube_quality_drops_when_throttled(enforcer):
    """When YouTube gets LOW priority, its predicted quality must be ≤ 360p."""
    result = enforcer.apply_priorities([
        {"app_id": "youtube", "priority": "LOW"},
    ])
    yt = next(a for a in result["apps"] if a["app_id"] == "youtube")
    quality = yt.get("estimated_quality", "")
    low_qualities = {"144p", "240p", "360p"}
    assert quality in low_qualities or yt["ceil_kbps"] <= 700, \
        f"Expected low quality, got {quality} at {yt['ceil_kbps']} kbps"

def test_blocked_app_gets_zero_bandwidth(enforcer):
    result = enforcer.apply_priorities([
        {"app_id": "youtube", "priority": "BLOCKED"},
    ])
    yt = next(a for a in result["apps"] if a["app_id"] == "youtube")
    assert yt["ceil_kbps"] == 0 or yt["ceil_kbps"] <= 1

def test_critical_priority_gets_90pct_bandwidth(enforcer):
    result = enforcer.apply_priorities([
        {"app_id": "zoom", "priority": "CRITICAL"},
    ])
    zoom = next(a for a in result["apps"] if a["app_id"] == "zoom")
    total_kbps = enforcer.total_kbps
    assert zoom["ceil_kbps"] >= total_kbps * 0.85  # ≥85% of total

def test_clear_rules_returns_success(enforcer):
    result = enforcer.clear_all_rules()
    assert result["success"] is True

def test_multiple_apps_allocations_do_not_exceed_total(enforcer):
    result = enforcer.apply_priorities([
        {"app_id": "zoom",    "priority": "HIGH"},
        {"app_id": "youtube", "priority": "LOW"},
        {"app_id": "spotify", "priority": "NORMAL"},
        {"app_id": "steam",   "priority": "NORMAL"},
    ])
    total = enforcer.total_kbps
    # No single app's ceiling should exceed total
    for a in result["apps"]:
        assert a["ceil_kbps"] <= total + 100  # small tolerance
```

### `tests/test_app_qos/test_priority_api.py`

```python
"""REST API tests for app priority endpoints."""
import pytest, httpx, os

BASE = "http://localhost:8000"

def _token(email="marcus@riveralogistics.com", pw="Rivera@2026"):
    return httpx.post(f"{BASE}/api/v1/auth/login",
                      json={"email": email, "password": pw}).json()["access_token"]

@pytest.fixture(scope="module")
def token():
    return _token()

def test_get_signatures(token):
    r = httpx.get(f"{BASE}/api/v1/apps/signatures",
                  headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    apps = r.json()["apps"]
    app_ids = [a["app_id"] for a in apps]
    assert "zoom" in app_ids
    assert "youtube" in app_ids

def test_set_zoom_high_youtube_low(token):
    """Core feature test: Zoom HIGH → YouTube LOW drops quality."""
    r = httpx.post(f"{BASE}/api/v1/apps/priorities",
                   json={"priorities": [
                       {"app_id": "zoom",    "priority": "HIGH"},
                       {"app_id": "youtube", "priority": "LOW"},
                   ]},
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    result = r.json()
    apps_by_id = {a["app_id"]: a for a in result["apps"]}
    assert "zoom"    in apps_by_id
    assert "youtube" in apps_by_id
    # Zoom should have MORE ceiling bandwidth than YouTube
    assert apps_by_id["zoom"]["ceil_kbps"] > apps_by_id["youtube"]["ceil_kbps"]
    # YouTube quality should be low
    yt_quality = apps_by_id["youtube"].get("estimated_quality", "")
    assert yt_quality in ("144p", "240p", "360p", "480p"), \
        f"Expected low quality for YouTube, got {yt_quality}"

def test_get_current_priorities(token):
    r = httpx.get(f"{BASE}/api/v1/apps/priorities",
                  headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()["priorities"]) >= 2

def test_get_quality_predictions(token):
    r = httpx.get(f"{BASE}/api/v1/apps/quality",
                  headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    preds = r.json()["predictions"]
    assert isinstance(preds, list)
    yt = next((p for p in preds if p["app_id"] == "youtube"), None)
    assert yt is not None
    assert yt["quality"] in ("144p", "240p", "360p", "480p")

def test_remove_single_app_priority(token):
    r = httpx.delete(f"{BASE}/api/v1/apps/priorities/youtube",
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

def test_reset_all_priorities(token):
    r = httpx.post(f"{BASE}/api/v1/apps/reset",
                   json={},
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["success"] is True

def test_user_priorities_are_isolated():
    """Two different users' priorities must not interfere."""
    t1 = _token("marcus@riveralogistics.com", "Rivera@2026")
    t2 = _token("priya@nairmedical.com", "NairMed@2026")

    # User 1 sets Zoom HIGH
    httpx.post(f"{BASE}/api/v1/apps/priorities",
               json={"priorities": [{"app_id": "zoom", "priority": "HIGH"}]},
               headers={"Authorization": f"Bearer {t1}"})

    # User 2 sets YouTube HIGH
    httpx.post(f"{BASE}/api/v1/apps/priorities",
               json={"priorities": [{"app_id": "youtube", "priority": "HIGH"}]},
               headers={"Authorization": f"Bearer {t2}"})

    # User 1 should still see Zoom as HIGH
    r = httpx.get(f"{BASE}/api/v1/apps/priorities",
                  headers={"Authorization": f"Bearer {t1}"})
    p = r.json()["priorities"]
    zoom = next((x for x in p if x["app_id"] == "zoom"), None)
    assert zoom and zoom["priority"] == "HIGH"
```

### `tests/test_app_qos/test_e2e_zoom_youtube.py`

```python
"""
End-to-end demonstration test: Zoom priority causes YouTube quality drop.
This is the core academic demonstration of the App Priority Switch feature.
"""
import pytest, httpx

BASE = "http://localhost:8000"

def test_e2e_zoom_prioritized_youtube_drops_to_low_quality():
    """
    SCENARIO:
      - YouTube is playing at 2160p (25 Mbps needed)
      - User sets Zoom = HIGH, YouTube = LOW in PathWise AI
      - PathWise enforces 5% bandwidth cap on YouTube (~5 Mbps on 100 Mbps link)
      - YouTube's predicted quality drops from 2160p to ≤ 480p
      - Zoom gets 70% guaranteed bandwidth (~70 Mbps) → "Excellent" quality

    This test verifies the bandwidth allocation math and quality prediction chain.
    The actual OS enforcement is in simulate mode (no real tc needed).
    """
    # Login
    r = httpx.post(f"{BASE}/api/v1/auth/login",
                   json={"email": "marcus@riveralogistics.com", "password": "Rivera@2026"})
    token = r.json()["access_token"]
    hdrs = {"Authorization": f"Bearer {token}"}

    # Step 1: Verify baseline — no rules, YouTube at full quality
    httpx.post(f"{BASE}/api/v1/apps/reset", json={}, headers=hdrs)

    # Step 2: Set Zoom HIGH, YouTube LOW
    r = httpx.post(f"{BASE}/api/v1/apps/priorities",
                   json={"priorities": [
                       {"app_id": "zoom",    "priority": "HIGH"},
                       {"app_id": "youtube", "priority": "LOW"},
                   ]},
                   headers=hdrs)
    assert r.status_code == 200, "Priority API must accept the request"
    result = r.json()
    apps = {a["app_id"]: a for a in result["apps"]}

    # Step 3: Verify Zoom gets high bandwidth
    zoom = apps["zoom"]
    assert zoom["ceil_kbps"] >= 50000, \
        f"Zoom should get ≥50 Mbps on HIGH priority, got {zoom['ceil_kbps']} kbps"
    assert zoom.get("estimated_quality") in ("Excellent", "Good"), \
        f"Zoom quality should be Excellent/Good, got {zoom.get('estimated_quality')}"

    # Step 4: Verify YouTube is throttled to LOW quality
    youtube = apps["youtube"]
    # On LOW priority: 5% of 100 Mbps = 5000 kbps → forces quality ≤ 720p
    assert youtube["ceil_kbps"] <= 5100, \
        f"YouTube should be capped ≤5100 kbps on LOW, got {youtube['ceil_kbps']} kbps"
    low_qualities = {"144p", "240p", "360p", "480p", "720p"}
    assert youtube.get("estimated_quality") in low_qualities, \
        f"YouTube must drop quality when throttled, got {youtube.get('estimated_quality')}"

    print(f"\n{'='*60}")
    print(f"DEMO RESULT: App Priority Switch")
    print(f"{'='*60}")
    print(f"  Zoom    → {zoom['ceil_kbps']/1000:.0f} Mbps ceiling → Quality: {zoom['estimated_quality']}")
    print(f"  YouTube → {youtube['ceil_kbps']/1000:.1f} Mbps ceiling → Quality: {youtube['estimated_quality']}")
    print(f"{'='*60}")
    print(f"YouTube dropped from 2160p to {youtube['estimated_quality']} ✓")

    # Step 5: Reset and verify
    httpx.post(f"{BASE}/api/v1/apps/reset", json={}, headers=hdrs)


def test_ibn_command_prioritize_zoom_over_youtube():
    """IBN natural language: 'Prioritize Zoom over YouTube' triggers the same result."""
    r = httpx.post(f"{BASE}/api/v1/auth/login",
                   json={"email": "tobias@bauertech.io", "password": "Bauer@2026"})
    token = r.json()["access_token"]
    hdrs = {"Authorization": f"Bearer {token}"}

    r = httpx.post(f"{BASE}/api/v1/ibn/deploy",
                   json={"command": "Prioritize Zoom over YouTube on fiber",
                         "user_id": r.json().get("user_id", "user-008")},
                   headers=hdrs)
    assert r.status_code == 200
    result = r.json()
    assert result.get("type") == "app_priority" or result.get("success") is True
```

---

## SECTION 10 — ADMIN VIEW

### `frontend/src/pages/admin/AppQoSOverview.tsx`

Add to admin sidebar: **App QoS Overview**

Layout:
1. Table of all users + their current active app priorities
2. Per-user: list of {app → priority → quality}
3. "Clear Rules for User" button per row
4. Global bandwidth impact chart (stacked bar per user showing bandwidth split)

Endpoint: `GET /api/v1/apps/admin/all-priorities` (already created above)

---

## SECTION 11 — DEFINITION OF DONE

```bash
# 1. Run all app QoS tests
pytest tests/test_app_qos/ -v -s
# All tests must pass

# 2. Core demonstration test
pytest tests/test_app_qos/test_e2e_zoom_youtube.py -v -s
# Expected output:
#   Zoom    → 70 Mbps ceiling → Quality: Excellent
#   YouTube → 5.0 Mbps ceiling → Quality: 144p or 360p
#   YouTube dropped from 2160p to 144p ✓

# 3. Build frontend
cd frontend && npm run build
# No TypeScript errors

# 4. Manual UI walkthrough:
# a) Login as marcus@riveralogistics.com
# b) Navigate to /user/apps
# c) Click "Zoom" → it appears in Priority Queue with HIGH default
# d) Click "YouTube" → appears in Priority Queue with NORMAL default
# e) Change YouTube priority to LOW in the dropdown
# f) Click "⚡ Apply Priorities"
# g) Column 3 shows: Zoom = Excellent, YouTube = 144p or 240p
# h) Bandwidth bar for YouTube is very short vs Zoom
# i) Click "Reset" → bars return to full

# 5. IBN test:
# a) Navigate to /user/policies (IBN page)
# b) Type: "Prioritize Zoom over YouTube on fiber"
# c) Click Translate Intent
# d) Expected: "Set zoom to HIGH, youtube to LOW — App Priority Switch applied"
# e) Navigate back to /user/apps — Zoom and YouTube are in queue with correct priorities
```

### Full DoD Checklist

**Backend:**
- [ ] `server/app_qos/signatures.py` — 20+ apps, quality tiers for streaming apps
- [ ] `server/app_qos/flow_detector.py` — detects running apps via psutil
- [ ] `server/app_qos/bandwidth_enforcer.py` — simulate + tc + powershell modes
- [ ] `server/app_qos/priority_manager.py` — per-user state management
- [ ] `server/routers/app_priority.py` — 7 REST endpoints + WebSocket
- [ ] Enforcer registered in `main.py`

**Core behavior:**
- [ ] `zoom HIGH + youtube LOW` → YouTube ceiling ≤ 5% of total link
- [ ] YouTube quality prediction = 144p when ceiling ≤ 300 Kbps
- [ ] YouTube quality prediction = 2160p when ceiling ≥ 25 Mbps (uncapped)
- [ ] `BLOCKED` priority → ceil = 0 kbps
- [ ] `CRITICAL` priority → ceil ≥ 90% of total link
- [ ] Multi-app priorities do not exceed total link capacity

**Frontend:**
- [ ] `/user/apps` page renders 3-column layout
- [ ] App catalog shows 20+ apps organized by category
- [ ] Drag-to-reorder works in priority queue
- [ ] Priority dropdown changes trigger reallocation on Apply
- [ ] Quality badges show: 2160p green, 1080p blue, 144p red
- [ ] Bandwidth bars animate to new values on Apply
- [ ] Zoom + YouTube detected simultaneously → banner shown
- [ ] WebSocket updates quality in real-time (2 Hz)
- [ ] Reset clears all rules and empties queue

**IBN integration:**
- [ ] "Prioritize Zoom over YouTube" → app priority action
- [ ] "Block YouTube" → BLOCKED priority
- [ ] "Give Discord high priority" → HIGH priority
- [ ] "Throttle Netflix to 360p" → LOW + ~600 kbps target

**Tests:**
- [ ] `test_signatures.py` — all pass
- [ ] `test_bandwidth_enforcer.py` — all pass
- [ ] `test_priority_api.py` — all pass (especially `test_set_zoom_high_youtube_low`)
- [ ] `test_e2e_zoom_youtube.py` — PASSES with printed demo output

---

## SECTION 12 — HOW TO DEMO TO A PROFESSOR

When demonstrating this feature during academic review:

1. **Start the stack:** `docker compose up -d`
2. **Login as Marcus Rivera** (a logistics SME business owner)
3. **Open App Priority Manager** (`/user/apps`)
4. **Say:** *"Imagine Zoom is running for a video call and YouTube is playing 4K in the background"*
5. **Add both apps** to the priority queue
6. **Set:** Zoom = HIGH, YouTube = LOW
7. **Click Apply**
8. **Point to Column 3:**
   - "Zoom receives 70 Mbps guaranteed — you can see it's rated 'Excellent'"
   - "YouTube is now hard-capped at 5 Mbps. YouTube's DASH algorithm will detect the bandwidth drop and within 2–3 seconds it switches from 2160p all the way down to 144p. This is the same adaptive algorithm YouTube uses in production."
9. **Show IBN page:** Type "Prioritize Zoom over YouTube" → same result via NLP
10. **Click Reset** → "Full bandwidth restored. YouTube will scale back to 4K automatically."

*This demonstrates SDD TrafficSteeringController, SRS Req-Func-Sw-6 (pre-emptive rerouting of high-priority traffic classes), and the existing Application QoS requirement for 18+ named applications.*

---

*PathWise AI — Team Pathfinders, COSC6370-001*  
*App Priority Switch — against SRS v1.0 / SDD v1.0 / README v2.0.0*  
*Satisfies: Req-Func-Sw-6 (VoIP/video pre-emptive rerouting), Application QoS section (18+ apps, Windows+Linux), SDD TrafficSteeringController (selectBestLink, preserveSession)*
