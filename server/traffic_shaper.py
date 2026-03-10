"""
Traffic Shaper — real OS-level bandwidth control for app-aware traffic management.

Uses Windows QoS policies (New-NetQosPolicy) and firewall rules to throttle
or prioritize traffic per application. Integrates with IBN for natural
language control.

Supported apps: Zoom, YouTube, Teams, Netflix, Spotify, Discord, Slack,
Gaming, Twitch, Google Meet, Skype, WhatsApp, Telegram, etc.

Requires: Administrator privileges for PowerShell QoS commands.
"""

from __future__ import annotations
import asyncio
import os
import re
import socket
import subprocess
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from server import audit


# ── App Definitions ────────────────────────────────────────────

class PriorityClass(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BLOCKED = "blocked"


@dataclass
class AppProfile:
    """Defines a network application for traffic shaping."""
    name: str
    display_name: str
    category: str
    process_names: list[str]
    domains: list[str]
    ip_prefixes: list[str]
    default_priority: PriorityClass = PriorityClass.NORMAL
    default_bandwidth_kbps: int = 0


APP_REGISTRY: dict[str, AppProfile] = {
    "zoom": AppProfile(
        name="zoom", display_name="Zoom", category="video_call",
        process_names=["Zoom.exe", "ZoomWebHost.exe"],
        domains=["*.zoom.us", "*.zoomgov.com"],
        ip_prefixes=["3.7.35.0/25", "3.21.137.128/25", "3.22.11.0/24",
                      "3.23.93.0/24", "3.25.41.128/25", "3.25.42.0/25",
                      "3.25.49.0/24", "8.5.128.0/23", "13.52.6.128/25",
                      "52.61.100.128/25", "64.125.62.0/24", "64.211.144.0/24"],
        default_priority=PriorityClass.CRITICAL,
    ),
    "youtube": AppProfile(
        name="youtube", display_name="YouTube", category="streaming",
        process_names=["chrome.exe", "msedge.exe", "firefox.exe"],
        domains=["*.googlevideo.com", "*.youtube.com", "*.ytimg.com"],
        ip_prefixes=["216.58.0.0/16", "142.250.0.0/15", "172.217.0.0/16",
                      "208.65.152.0/22", "208.117.224.0/19"],
        default_priority=PriorityClass.LOW,
    ),
    "teams": AppProfile(
        name="teams", display_name="Microsoft Teams", category="video_call",
        process_names=["ms-teams.exe", "Teams.exe", "msteams.exe"],
        domains=["*.teams.microsoft.com", "*.skype.com", "*.lync.com"],
        ip_prefixes=["13.107.64.0/18", "52.112.0.0/14", "52.120.0.0/14"],
        default_priority=PriorityClass.CRITICAL,
    ),
    "netflix": AppProfile(
        name="netflix", display_name="Netflix", category="streaming",
        process_names=["chrome.exe", "msedge.exe", "Netflix.exe"],
        domains=["*.netflix.com", "*.nflxvideo.net", "*.nflximg.net"],
        ip_prefixes=["23.246.0.0/18", "37.77.184.0/21", "38.72.126.0/24",
                      "45.57.0.0/17", "64.120.128.0/17", "66.197.128.0/17",
                      "69.53.224.0/19", "108.175.32.0/20"],
        default_priority=PriorityClass.LOW,
    ),
    "spotify": AppProfile(
        name="spotify", display_name="Spotify", category="streaming",
        process_names=["Spotify.exe"],
        domains=["*.spotify.com", "*.spotifycdn.com", "*.scdn.co"],
        ip_prefixes=["35.186.224.0/20", "104.154.0.0/15"],
        default_priority=PriorityClass.LOW,
    ),
    "discord": AppProfile(
        name="discord", display_name="Discord", category="social",
        process_names=["Discord.exe", "Update.exe"],
        domains=["*.discord.com", "*.discord.gg", "*.discordapp.com", "*.discord.media"],
        ip_prefixes=["162.159.128.0/17", "66.22.196.0/22"],
        default_priority=PriorityClass.NORMAL,
    ),
    "slack": AppProfile(
        name="slack", display_name="Slack", category="business",
        process_names=["slack.exe"],
        domains=["*.slack.com", "*.slack-edge.com", "*.slack-msgs.com"],
        ip_prefixes=["54.192.0.0/16"],
        default_priority=PriorityClass.HIGH,
    ),
    "gaming": AppProfile(
        name="gaming", display_name="Online Gaming", category="gaming",
        process_names=["steam.exe", "EpicGamesLauncher.exe", "Battle.net.exe",
                        "valorant.exe", "FortniteClient-Win64-Shipping.exe"],
        domains=["*.steampowered.com", "*.epicgames.com", "*.battle.net"],
        ip_prefixes=["208.64.200.0/24", "205.185.192.0/18"],
        default_priority=PriorityClass.NORMAL,
    ),
    "twitch": AppProfile(
        name="twitch", display_name="Twitch", category="streaming",
        process_names=["chrome.exe", "msedge.exe"],
        domains=["*.twitch.tv", "*.ttvnw.net", "*.jtvnw.net"],
        ip_prefixes=["52.223.192.0/18", "99.181.64.0/18"],
        default_priority=PriorityClass.LOW,
    ),
    "google_meet": AppProfile(
        name="google_meet", display_name="Google Meet", category="video_call",
        process_names=["chrome.exe", "msedge.exe"],
        domains=["*.meet.google.com", "meet.google.com"],
        ip_prefixes=["74.125.250.0/24", "142.250.82.0/24"],
        default_priority=PriorityClass.CRITICAL,
    ),
    "skype": AppProfile(
        name="skype", display_name="Skype", category="video_call",
        process_names=["Skype.exe", "SkypeApp.exe"],
        domains=["*.skype.com", "*.lync.com"],
        ip_prefixes=["13.107.64.0/18", "52.112.0.0/14"],
        default_priority=PriorityClass.CRITICAL,
    ),
    "whatsapp": AppProfile(
        name="whatsapp", display_name="WhatsApp", category="social",
        process_names=["WhatsApp.exe"],
        domains=["*.whatsapp.net", "*.whatsapp.com"],
        ip_prefixes=["31.13.64.0/18", "157.240.0.0/16"],
        default_priority=PriorityClass.HIGH,
    ),
    "telegram": AppProfile(
        name="telegram", display_name="Telegram", category="social",
        process_names=["Telegram.exe"],
        domains=["*.telegram.org", "*.t.me"],
        ip_prefixes=["91.108.4.0/22", "91.108.8.0/22", "91.108.12.0/22",
                      "91.108.16.0/22", "91.108.20.0/22", "149.154.160.0/20"],
        default_priority=PriorityClass.NORMAL,
    ),
    "web_browsing": AppProfile(
        name="web_browsing", display_name="Web Browsing", category="bulk",
        process_names=["chrome.exe", "msedge.exe", "firefox.exe"],
        domains=[],
        ip_prefixes=[],
        default_priority=PriorityClass.NORMAL,
    ),
    "file_transfer": AppProfile(
        name="file_transfer", display_name="File Transfers", category="bulk",
        process_names=["OneDrive.exe", "Dropbox.exe", "googledrivesync.exe"],
        domains=["*.dropbox.com", "*.onedrive.com", "*.googleapis.com"],
        ip_prefixes=[],
        default_priority=PriorityClass.LOW,
    ),
}

APP_ALIASES: dict[str, str] = {
    "zoom": "zoom", "zoom call": "zoom", "zoom meeting": "zoom",
    "youtube": "youtube", "yt": "youtube", "youtube video": "youtube",
    "teams": "teams", "microsoft teams": "teams", "ms teams": "teams",
    "netflix": "netflix",
    "spotify": "spotify", "music": "spotify",
    "discord": "discord",
    "slack": "slack",
    "gaming": "gaming", "games": "gaming", "steam": "gaming", "fortnite": "gaming", "valorant": "gaming",
    "twitch": "twitch", "twitch stream": "twitch",
    "google meet": "google_meet", "gmeet": "google_meet",
    "skype": "skype",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "browsing": "web_browsing", "web": "web_browsing", "chrome": "web_browsing",
    "file transfer": "file_transfer", "onedrive": "file_transfer", "dropbox": "file_transfer",
}

BANDWIDTH_PRESETS = {
    PriorityClass.CRITICAL: 0,
    PriorityClass.HIGH: 0,
    PriorityClass.NORMAL: 10_000_000,
    PriorityClass.LOW: 500_000,
    PriorityClass.BLOCKED: 1,
}


# ── Active Traffic Policy ──────────────────────────────────────

@dataclass
class TrafficPolicy:
    id: str
    app_name: str
    display_name: str
    action: str
    bandwidth_kbps: int
    priority: PriorityClass
    created_at: float
    created_by: str
    qos_policy_name: str
    active: bool = True
    reason: str = ""


_policy_history: deque[TrafficPolicy] = deque(maxlen=100)
_rule_counter = 0


# ── Resolve App IPs via DNS ────────────────────────────────────

def _lookup_domain_ips(domain_list: list[str]) -> list[str]:
    """Resolve domain patterns to IP addresses for QoS targeting."""
    resolved = []
    for entry in domain_list:
        stripped = entry.lstrip("*.")
        try:
            addr_results = socket.getaddrinfo(stripped, None, socket.AF_INET)
            for _, _, _, _, (ip_addr, _) in addr_results:
                if ip_addr not in resolved:
                    resolved.append(ip_addr)
        except (socket.gaierror, OSError):
            pass
    return resolved


# ── PowerShell Execution (elevated) ───────────────────────────

_SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "infra", "qos_scripts")
os.makedirs(_SCRIPT_DIR, exist_ok=True)


def _execute_powershell(command: str, need_admin: bool = True) -> tuple[bool, str]:
    """
    Execute a PowerShell command. If need_admin=True, writes to a script
    and executes with elevation via Start-Process -Verb RunAs.
    """
    if need_admin:
        return _execute_elevated(command)

    try:
        proc_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=10,
        )
        combined_out = proc_result.stdout.strip() + proc_result.stderr.strip()
        return proc_result.returncode == 0, combined_out
    except Exception as exc:
        return False, str(exc)


def _execute_elevated(command: str) -> tuple[bool, str]:
    """
    Execute PowerShell with admin elevation.
    Writes commands to a .ps1 script, launches it elevated, waits for completion.
    """
    script_file = os.path.join(_SCRIPT_DIR, f"qos_cmd_{int(time.time()*1000)}.ps1")
    output_file = script_file + ".result"

    escaped_output = output_file.replace("\\", "\\\\")
    ps_script = f"""
$ErrorActionPreference = "Continue"
$capturedLines = @()
try {{
{command}
    $capturedLines += "OK"
}} catch {{
    $capturedLines += "FAIL"
    $capturedLines += $_.Exception.Message
}}
$capturedLines -join "`n" | Out-File -FilePath "{escaped_output}" -Encoding UTF8
"""
    with open(script_file, "w") as fh:
        fh.write(ps_script)

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f'Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File {script_file}" '
             f'-Verb RunAs -Wait -WindowStyle Hidden'],
            capture_output=True, text=True, timeout=15,
        )

        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8-sig") as fh:
                raw_output = fh.read().strip()
            os.remove(output_file)
            succeeded = "OK" in raw_output
            if not succeeded:
                print(f"[traffic_shaper] Elevated PS error: {raw_output}")
            return succeeded, raw_output
        else:
            return False, "UAC denied or script failed"

    except subprocess.TimeoutExpired:
        return False, "Elevated command timed out"
    except Exception as exc:
        return False, str(exc)
    finally:
        try:
            os.remove(script_file)
        except OSError:
            pass


def _apply_qos_throttle(rule_name: str, app: AppProfile, rate_bps: int) -> bool:
    """
    Create Windows QoS + Firewall rules to throttle an app.

    Uses a multi-strategy approach:
      1. QoS by process name (best for native apps like Zoom.exe, Spotify.exe)
      2. QoS by destination IP prefix (for browser-based apps like YouTube)
      3. QoS by resolved domain IPs (dynamic, catches CDN IPs)
      4. Firewall rate-limit as fallback (block if rate_bps <= 1000)
    """
    rule_commands = []

    # Collect all target IPs (static ranges + DNS-resolved)
    combined_prefixes = list(app.ip_prefixes[:5])
    dns_ips = _lookup_domain_ips(app.domains[:5])
    for addr in dns_ips[:8]:
        combined_prefixes.append(f"{addr}/32")

    # Strategy 1: Throttle by process name
    browser_processes = ("chrome.exe", "msedge.exe", "firefox.exe")
    if app.process_names and app.process_names[0] not in browser_processes:
        rule_commands.append(
            f'New-NetQosPolicy -Name "{rule_name}" '
            f'-AppPathNameMatchCondition "{app.process_names[0]}" '
            f'-ThrottleRateActionBitsPerSecond {rate_bps} '
            f'-PolicyStore ActiveStore'
        )

    # Strategy 2: Throttle by destination IP prefix
    for idx, cidr in enumerate(combined_prefixes):
        sub_rule = f"{rule_name}-r{idx}"
        rule_commands.append(
            f'New-NetQosPolicy -Name "{sub_rule}" '
            f'-IPDstPrefixMatchCondition "{cidr}" '
            f'-ThrottleRateActionBitsPerSecond {rate_bps} '
            f'-PolicyStore ActiveStore'
        )

    # Strategy 3: Block QUIC/UDP to force TCP (YouTube/Netflix use QUIC
    # which bypasses QoS). Blocking UDP 443 forces fallback to TCP.
    target_ips = list(app.ip_prefixes[:5])
    extra_resolved = _lookup_domain_ips(app.domains[:3])
    target_ips.extend(f"{addr}/32" for addr in extra_resolved[:5])
    if target_ips:
        fw_addr_list = ",".join(f'"{p}"' for p in target_ips)
        rule_commands.append(
            f'New-NetFirewallRule -DisplayName "{rule_name}-quic" '
            f'-Direction Outbound -Action Block '
            f'-Protocol UDP -RemotePort 443 '
            f'-RemoteAddress {fw_addr_list} '
            f'-Enabled True'
        )

    # Strategy 4: Full block via firewall if rate is effectively zero
    if rate_bps <= 1000:
        if target_ips:
            fw_addr_list2 = ",".join(f'"{p}"' for p in target_ips)
            rule_commands.append(
                f'New-NetFirewallRule -DisplayName "{rule_name}-block" '
                f'-Direction Outbound -Action Block '
                f'-RemoteAddress {fw_addr_list2} '
                f'-Enabled True'
            )

    if not rule_commands:
        print(f"[traffic_shaper] No throttle rules generated for {app.name}")
        return False

    merged_cmd = "\n".join(rule_commands)
    success, msg = _execute_powershell(merged_cmd)
    if success:
        print(f"[traffic_shaper] QoS applied: {len(rule_commands)} rules for {app.display_name} @ {rate_bps/1000:.0f} Kbps")
    else:
        print(f"[traffic_shaper] QoS apply failed for {app.display_name}: {msg}")
    return success


def _cleanup_qos_rules(rule_name: str) -> bool:
    """Remove all QoS policies and firewall rules matching a name pattern."""
    cleanup_cmd = (
        f'Get-NetQosPolicy -PolicyStore ActiveStore -ErrorAction SilentlyContinue | '
        f'Where-Object {{ $_.Name -like "{rule_name}*" }} | '
        f'Remove-NetQosPolicy -Confirm:$false -ErrorAction SilentlyContinue\n'
        f'Get-NetFirewallRule -ErrorAction SilentlyContinue | '
        f'Where-Object {{ $_.DisplayName -like "{rule_name}*" }} | '
        f'Remove-NetFirewallRule -ErrorAction SilentlyContinue'
    )
    result, _ = _execute_powershell(cleanup_cmd)
    return result


# ── Public API ─────────────────────────────────────────────────

def throttle_app(app_name: str, bandwidth_kbps: int = 500, reason: str = "", created_by: str = "manual") -> Optional[TrafficPolicy]:
    """
    Throttle an application to a specified bandwidth.
    bandwidth_kbps=500 forces YouTube/Netflix to drop to 144p/240p.
    """
    global _rule_counter
    target_app = APP_REGISTRY.get(app_name)
    if not target_app:
        return None

    _rule_counter += 1
    rule_label = f"PathWise-{app_name}-{_rule_counter}"
    rate_in_bps = bandwidth_kbps * 1000

    _apply_qos_throttle(rule_label, target_app, rate_in_bps)

    new_policy = TrafficPolicy(
        id=str(uuid.uuid4())[:8],
        app_name=app_name,
        display_name=target_app.display_name,
        action="throttle",
        bandwidth_kbps=bandwidth_kbps,
        priority=PriorityClass.LOW,
        created_at=time.time(),
        created_by=created_by,
        qos_policy_name=rule_label,
        reason=reason or f"Throttled {target_app.display_name} to {bandwidth_kbps} Kbps",
    )
    _policy_history.append(new_policy)

    audit.log_event(
        "POLICY_CHANGE", actor="SYSTEM",
        policy_change={"action": "throttle", "app": app_name, "bandwidth_kbps": bandwidth_kbps},
        details=new_policy.reason,
    )

    print(f"[traffic_shaper] Throttled {target_app.display_name} to {bandwidth_kbps} Kbps")
    return new_policy


def prioritize_app(app_name: str, reason: str = "", created_by: str = "manual") -> Optional[TrafficPolicy]:
    """Remove any throttle on an app and mark it as prioritized."""
    global _rule_counter
    target_app = APP_REGISTRY.get(app_name)
    if not target_app:
        return None

    for existing in _policy_history:
        if existing.app_name == app_name and existing.active:
            _cleanup_qos_rules(existing.qos_policy_name)
            existing.active = False

    _rule_counter += 1
    new_policy = TrafficPolicy(
        id=str(uuid.uuid4())[:8],
        app_name=app_name,
        display_name=target_app.display_name,
        action="prioritize",
        bandwidth_kbps=0,
        priority=PriorityClass.CRITICAL,
        created_at=time.time(),
        created_by=created_by,
        qos_policy_name=f"PathWise-pri-{app_name}-{_rule_counter}",
        reason=reason or f"Prioritized {target_app.display_name} — unlimited bandwidth",
    )
    _policy_history.append(new_policy)

    audit.log_event(
        "POLICY_CHANGE", actor="SYSTEM",
        policy_change={"action": "prioritize", "app": app_name},
        details=new_policy.reason,
    )

    print(f"[traffic_shaper] Prioritized {target_app.display_name}")
    return new_policy


def remove_policy(policy_id: str) -> bool:
    """Remove a traffic policy and restore normal bandwidth."""
    for entry in _policy_history:
        if entry.id == policy_id and entry.active:
            _cleanup_qos_rules(entry.qos_policy_name)
            entry.active = False

            audit.log_event(
                "POLICY_CHANGE", actor="SYSTEM",
                policy_change={"action": "remove", "app": entry.app_name, "policy_id": entry.id},
                details=f"Removed {entry.action} policy on {entry.display_name}",
            )
            print(f"[traffic_shaper] Removed policy on {entry.display_name}")
            return True
    return False


def remove_all_policies():
    """Remove all active traffic shaping policies — full cleanup."""
    for entry in _policy_history:
        if entry.active:
            entry.active = False

    global_cleanup = (
        'Get-NetQosPolicy -PolicyStore ActiveStore -ErrorAction SilentlyContinue | '
        'Where-Object { $_.Name -like "PathWise-*" } | '
        'Remove-NetQosPolicy -Confirm:$false -ErrorAction SilentlyContinue\n'
        'Get-NetFirewallRule -ErrorAction SilentlyContinue | '
        'Where-Object { $_.DisplayName -like "PathWise-*" } | '
        'Remove-NetFirewallRule -ErrorAction SilentlyContinue'
    )
    _execute_powershell(global_cleanup)
    print("[traffic_shaper] All QoS policies and firewall rules removed")


def prioritize_over(high_app: str, low_app: str, throttle_kbps: int = 500, reason: str = "", created_by: str = "manual") -> list[TrafficPolicy]:
    """
    Prioritize one app over another.
    High app gets unlimited bandwidth, low app gets throttled.
    """
    result_policies = []
    high_policy = prioritize_app(high_app, reason=reason or f"Prioritized over {low_app}", created_by=created_by)
    if high_policy:
        result_policies.append(high_policy)
    low_policy = throttle_app(low_app, bandwidth_kbps=throttle_kbps,
                               reason=reason or f"Throttled in favor of {high_app}", created_by=created_by)
    if low_policy:
        result_policies.append(low_policy)
    return result_policies


# ── Query ──────────────────────────────────────────────────────

def get_active_policies() -> list[dict]:
    return [
        {
            "id": p.id,
            "app_name": p.app_name,
            "display_name": p.display_name,
            "action": p.action,
            "bandwidth_kbps": p.bandwidth_kbps,
            "priority": p.priority.value,
            "created_at": p.created_at,
            "created_by": p.created_by,
            "active": p.active,
            "reason": p.reason,
            "age_seconds": round(time.time() - p.created_at, 1),
        }
        for p in _policy_history if p.active
    ]


def get_all_policies() -> list[dict]:
    return [
        {
            "id": p.id,
            "app_name": p.app_name,
            "display_name": p.display_name,
            "action": p.action,
            "bandwidth_kbps": p.bandwidth_kbps,
            "priority": p.priority.value,
            "active": p.active,
            "reason": p.reason,
            "created_at": p.created_at,
            "age_seconds": round(time.time() - p.created_at, 1),
        }
        for p in _policy_history
    ]


def get_app_list() -> list[dict]:
    """Return all known apps for the UI dropdown."""
    return [
        {
            "name": app.name,
            "display_name": app.display_name,
            "category": app.category,
            "default_priority": app.default_priority.value,
        }
        for app in APP_REGISTRY.values()
    ]


def resolve_app_name(text: str) -> Optional[str]:
    """Resolve a natural language app reference to a registry key."""
    normalized = text.lower().strip()
    if normalized in APP_REGISTRY:
        return normalized
    for alias, mapped_name in sorted(APP_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in normalized:
            return mapped_name
    return None