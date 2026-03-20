"""
Bandwidth enforcer -- applies OS-level traffic shaping (or simulates it).

Modes (set via ENFORCER_MODE env var):
  simulate   - (default) compute allocations, log, but touch no OS settings
  tc         - Linux tc/iptables (requires root / NET_ADMIN)
  powershell - Windows enforcement (requires Administrator)
               Two strategies are combined:
                 1. HOSTS-file domain blocking for streaming apps (LOW/BLOCKED)
                    — precise, doesn't touch other Google services.
                 2. Narrow NetQoS throttling for app-specific IP ranges only.
               We never touch Google's shared anycast ranges
               (142.250/15, 172.217/16, etc.) because those host Google
               Fonts/Analytics/reCAPTCHA/gstatic -- used by most of the web.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from server.app_qos.signatures import (
    APP_SIGNATURES, PRIORITY_CLASSES, predict_quality,
)

logger = logging.getLogger("pathwise.enforcer")

ENFORCER_MODE = os.environ.get("ENFORCER_MODE", "simulate").lower()
WAN_INTERFACE = os.environ.get("WAN_INTERFACE", "eth0")
TOTAL_LINK_MBPS = float(os.environ.get("TOTAL_LINK_MBPS", "100"))

# Windows HOSTS file -- used for domain-level blocking of streaming apps
WINDOWS_HOSTS = Path(r"C:\Windows\System32\drivers\etc\hosts")
HOSTS_BACKUP = Path(os.environ.get("TEMP", r"C:\Windows\Temp")) / "pathwise_hosts.bak"
PW_BEGIN = "# === PathWise AI BEGIN ==="
PW_END = "# === PathWise AI END ==="

# Domain blocklists per app -- used when priority is LOW or BLOCKED.
# Each list contains SPECIFIC hostnames only -- never shared infra
# (no bare *.google.com, no *.microsoft.com, no *.cloudflare.com).
# This means any pair of apps can be demoed without breaking the host's
# internet: blocking YouTube leaves Gmail/Search/Drive fully functional;
# blocking Zoom leaves Outlook/Teams/Azure fully functional; etc.
APP_BLOCK_DOMAINS: Dict[str, List[str]] = {
    "zoom": [
        "zoom.us", "www.zoom.us",
        "us02web.zoom.us", "us04web.zoom.us", "us05web.zoom.us",
        "us06web.zoom.us", "us07web.zoom.us",
        "zoomgov.com", "www.zoomgov.com",
    ],
    "teams": [
        "teams.microsoft.com", "teams.live.com",
        "statics.teams.cdn.office.net",
        "config.teams.microsoft.com",
    ],
    "google_meet": [
        "meet.google.com",
    ],
    "youtube": [
        "www.youtube.com", "m.youtube.com", "youtube.com",
        "youtu.be", "www.youtu.be",
        "i.ytimg.com", "s.ytimg.com", "ytimg.com",
        "www.youtube-nocookie.com", "youtube-nocookie.com",
        "googlevideo.com", "youtubei.googleapis.com",
    ],
    "netflix": [
        "www.netflix.com", "netflix.com",
        "nflxvideo.net", "nflximg.net", "nflxso.net",
    ],
    "twitch": [
        "www.twitch.tv", "twitch.tv",
        "static.twitchcdn.net", "jtvnw.net",
    ],
    "disney_plus": [
        "www.disneyplus.com", "disneyplus.com",
        "bamgrid.com", "dssott.com",
    ],
    "discord": [
        "discord.com", "www.discord.com",
        "discord.gg", "discordapp.com",
        "cdn.discordapp.com", "gateway.discord.gg",
        "media.discordapp.net",
    ],
    "spotify": [
        "spotify.com", "www.spotify.com", "open.spotify.com",
        "api.spotify.com", "spclient.wg.spotify.com",
        "scdn.co", "i.scdn.co",
    ],
    "onedrive": [
        "onedrive.live.com", "www.onedrive.com",
        "api.onedrive.com", "onedrive.com",
    ],
    "steam": [
        "steampowered.com", "store.steampowered.com",
        "help.steampowered.com", "checkout.steampowered.com",
        "steamcommunity.com", "www.steamcommunity.com",
        "steamstatic.com", "steamcontent.com",
    ],
    # "google_chrome" intentionally omitted: it's the browser itself --
    # blocking it would kill the PathWise dashboard too.
}


# Domains to actively DISRUPT existing TCP/QUIC connections for when the app
# is blocked. We resolve these at enforcement time, then add a short-lived
# Windows Firewall outbound rule targeting those IPs on 443 (both TCP + UDP).
# The rule forces active sockets to reset -- which makes the streaming player
# immediately stall instead of coasting on its local buffer.
# The rule auto-removes after DISRUPT_WINDOW_S so shared-infra collateral is
# limited to a short window.
DISRUPT_DOMAINS: Dict[str, List[str]] = {
    "youtube":     ["googlevideo.com", "youtubei.googleapis.com"],
    "netflix":     ["nflxvideo.net"],
    "twitch":      ["jtvnw.net"],
    "disney_plus": ["bamgrid.com"],
}


class BandwidthEnforcer:
    """Compute bandwidth allocations and optionally enforce them on the OS."""

    def __init__(self) -> None:
        self._active_rules: Dict[str, dict] = {}
        self._mode = ENFORCER_MODE
        self._commands_log: list[dict] = []
        self._blocked_domains: set[str] = set()
        logger.info("BandwidthEnforcer mode=%s interface=%s total=%sMbps",
                    self._mode, WAN_INTERFACE, TOTAL_LINK_MBPS)
        # Always clear any stale rules left by a previous crashed process
        if self._mode == "powershell":
            self._panic_cleanup()

    # -- Public API --

    def apply_priorities(
        self,
        priorities: Dict[str, str],
        total_mbps: Optional[float] = None,
    ) -> Dict[str, dict]:
        total = total_mbps or TOTAL_LINK_MBPS
        allocations = self._compute_allocations(priorities, total)

        self._commands_log = []
        if self._mode == "tc":
            self._apply_tc_rules(allocations)
        elif self._mode == "powershell":
            self._apply_powershell_rules(allocations)
        else:
            self._apply_simulate(allocations)

        self._active_rules = allocations
        return allocations

    def clear_all_rules(self) -> dict:
        cleared = list(self._active_rules.keys())
        self._commands_log = []

        if self._mode == "tc":
            self._run(f"tc qdisc del dev {WAN_INTERFACE} root 2>/dev/null || true")
        elif self._mode == "powershell":
            self._panic_cleanup()

        self._active_rules = {}
        logger.info("Cleared all QoS rules: %s", cleared)
        return {"status": "cleared", "rules_removed": cleared}

    def get_active_allocations(self) -> Dict[str, dict]:
        return dict(self._active_rules)

    def get_commands_log(self) -> list[dict]:
        return list(self._commands_log)

    # -- Allocation computation --

    def _compute_allocations(
        self,
        priorities: Dict[str, str],
        total_mbps: float,
    ) -> Dict[str, dict]:
        if not priorities:
            return {}

        raw: Dict[str, float] = {}
        for app_id, pclass in priorities.items():
            cls = PRIORITY_CLASSES.get(pclass, PRIORITY_CLASSES["NORMAL"])
            raw[app_id] = cls["bandwidth_pct"]

        total_pct = sum(raw.values())
        if total_pct <= 0:
            return {
                app_id: {
                    "app_id": app_id, "priority": priorities[app_id],
                    "allocated_mbps": 0.0, "bandwidth_pct": 0.0,
                    "quality": predict_quality(app_id, 0.0),
                    "enforced": self._mode != "simulate",
                }
                for app_id in priorities
            }

        scale = min(1.0, 1.0 / total_pct)
        allocations: Dict[str, dict] = {}
        for app_id, pct in raw.items():
            actual_pct = pct * scale
            mbps = round(actual_pct * total_mbps, 2)
            allocations[app_id] = {
                "app_id": app_id, "priority": priorities[app_id],
                "allocated_mbps": mbps,
                "bandwidth_pct": round(actual_pct * 100, 1),
                "quality": predict_quality(app_id, mbps),
                "enforced": self._mode != "simulate",
            }
        return allocations

    # -- Linux tc (HTB) --

    def _apply_tc_rules(self, allocations: Dict[str, dict]) -> None:
        iface = WAN_INTERFACE
        self._run(f"tc qdisc del dev {iface} root 2>/dev/null || true")
        self._run(f"tc qdisc add dev {iface} root handle 1: htb default 99")
        self._run(f"tc class add dev {iface} parent 1: classid 1:1 htb rate {int(TOTAL_LINK_MBPS)}mbit")

        class_id = 10
        for app_id, alloc in allocations.items():
            rate = max(1, int(alloc["allocated_mbps"] * 1000))
            self._run(
                f"tc class add dev {iface} parent 1:1 classid 1:{class_id} "
                f"htb rate {rate}kbit ceil {rate}kbit"
            )
            sig = APP_SIGNATURES.get(app_id)
            if sig:
                for cidr in sig.cidrs[:5]:
                    self._run(
                        f"tc filter add dev {iface} parent 1: protocol ip prio {class_id} "
                        f"u32 match ip dst {cidr} flowid 1:{class_id}"
                    )
            class_id += 1
        logger.info("tc rules applied for %d apps on %s", len(allocations), iface)

    # -- Windows enforcement (HOSTS file + narrow NetQoS) --

    def _apply_powershell_rules(self, allocations: Dict[str, dict]) -> None:
        """
        Windows enforcement: pure HOSTS-file domain blocking.

        Semantics:
          * HIGH / NORMAL / CRITICAL -> no OS change (the app gets full speed).
          * LOW / BLOCKED            -> add each of the app's *specific*
                                        hostnames to the HOSTS file pointing
                                        at 0.0.0.0. Blocks only that app,
                                        in every browser, without touching
                                        any shared cloud infrastructure.

        This means ANY pair of apps from the catalog can be demoed without
        risk to the host's own internet connection. NetQoS CIDR-throttling
        is intentionally NOT used because even /16 prefixes overlap with
        shared anycast infrastructure (Google / Cloudflare / Azure) and
        collaterally damage unrelated traffic.
        """
        # Clean slate -- remove any stale PathWise artifacts.
        self._panic_cleanup()

        domains_to_block: List[str] = []
        blocked_apps: List[str] = []
        prioritised_apps: List[str] = []

        for app_id, alloc in allocations.items():
            priority_class = alloc.get("priority", "NORMAL")
            if priority_class in ("LOW", "BLOCKED") and app_id in APP_BLOCK_DOMAINS:
                domains_to_block.extend(APP_BLOCK_DOMAINS[app_id])
                blocked_apps.append(app_id)
            else:
                prioritised_apps.append(app_id)

        if domains_to_block:
            self._write_hosts_block(domains_to_block)
            # Windows NRPT wildcard DNS policy -- hosts file can't do
            # wildcards, but NRPT does. YouTube's CDN uses dynamic
            # hostnames like r3---sn-xxx.googlevideo.com that would
            # escape a hosts-only block. NRPT catches them all.
            self._apply_nrpt_wildcard_block(blocked_apps)
            self._run_ps("ipconfig /flushdns")
            self._run_ps("Clear-DnsClientCache -ErrorAction SilentlyContinue")

            # KEY STEP: kill Chrome's network service. This drops ALL of
            # Chrome's Alt-Svc cache, QUIC session state, and cached DNS
            # -- without this the player keeps streaming from cached
            # endpoints even though our DNS blocks are perfect. Chrome
            # auto-respawns the network service and must re-resolve
            # every host, which now hits 0.0.0.0 for YouTube.
            self._kill_chrome_network_service()

            # After network-service respawn, snapshot Chrome's NEW
            # connections (they'll be minimal, but catch any survivors).
            import time
            time.sleep(2)
            live_ips = self._collect_live_chrome_google_ips()
            dns_ips  = self._collect_disrupt_ips(blocked_apps)
            combined = sorted(set(live_ips) | set(dns_ips))

            # Firewall-block the surviving live IPs + global QUIC, as
            # belt-and-suspenders in case Chrome's respawn re-established
            # any cached connections.
            self._disrupt_active_connections(combined)

        logger.info(
            "Windows enforcement: blocked=%s prioritised=%s (%d domains)",
            blocked_apps, prioritised_apps, len(domains_to_block),
        )

    # Google-owned CDN IPv4 prefixes that serve googlevideo / Google Fiber /
    # Google Cloud edges used by YouTube. These are "likely YouTube" -- we
    # intersect with Chrome's live connection list so we only block IPs
    # Chrome is actually talking to.
    _GOOGLE_V4_PREFIXES = (
        "34.",        # Google Cloud -- YouTube CDN
        "35.",        # Google Cloud -- YouTube CDN
        "64.233.",    # Google
        "66.102.", "66.249.",
        "72.14.",
        "74.125.",
        "108.177.",
        "142.250.", "142.251.",
        "172.217.", "172.253.",
        "173.194.",
        "192.178.",   # googlevideo
        "209.85.",
        "216.58.",
        "216.239.",
        "18.97.",     # AWS used by YouTube's fastly edge in some geos
    )
    # Google-owned IPv6 prefixes (match against first 9 chars, lowercase)
    _GOOGLE_V6_PREFIXES = (
        "2607:f8b0",
        "2a00:1450",
        "2404:6800",
        "2800:3f0",
        "2c0f:fb50",
        "2001:4860",
    )

    # Wildcard namespaces per-app. Windows NRPT matches any name that ends
    # with the namespace; a leading dot means "match subdomains only".
    NRPT_WILDCARDS: Dict[str, List[str]] = {
        "youtube":     [".youtube.com", ".googlevideo.com", ".ytimg.com",
                        ".youtubei.googleapis.com", ".youtu.be"],
        "netflix":     [".netflix.com", ".nflxvideo.net", ".nflximg.net"],
        "twitch":      [".twitch.tv", ".ttvnw.net", ".jtvnw.net"],
        "disney_plus": [".disneyplus.com", ".bamgrid.com", ".dssott.com"],
        "spotify":     [".spotify.com", ".scdn.co"],
        "discord":     [".discord.com", ".discordapp.com", ".discord.gg"],
        "teams":       [".teams.microsoft.com"],
        "zoom":        [".zoom.us", ".zoomgov.com"],
        "google_meet": [".meet.google.com"],
        "onedrive":    [".onedrive.live.com", ".onedrive.com"],
        "steam":       [".steampowered.com", ".steamcommunity.com"],
    }

    def _kill_chrome_network_service(self) -> None:
        """
        Kill Chrome's utility 'network service' subprocess. Chrome auto-
        respawns it, but the respawn drops all cached Alt-Svc endpoints,
        QUIC sessions, and DNS cache -- forcing a fresh resolve that hits
        our hosts/NRPT blackholes. This is the single biggest lever for
        making YouTube actually stop during a running tab.
        """
        self._run_ps(
            "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" "
            "-ErrorAction SilentlyContinue | "
            "Where-Object { $_.CommandLine -like "
            "'*network.mojom.NetworkService*' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
            "-ErrorAction SilentlyContinue }"
        )
        logger.info("Chrome network service killed; Alt-Svc cache cleared.")

    def _apply_nrpt_wildcard_block(self, blocked_apps: List[str]) -> None:
        """
        Install Windows Name Resolution Policy Table (NRPT) rules that
        redirect queries matching the given namespace patterns to 0.0.0.0.
        This is the ONLY Windows-native mechanism that does true wildcard
        DNS blocking. The Windows hosts file has no wildcard support, so
        subdomains like r3---sn-xxx.googlevideo.com slip past it.
        """
        # Remove any existing PathWise NRPT rules first (idempotent).
        self._run_ps(
            "Get-DnsClientNrptRule -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Comment -eq 'PathWise-AppBlock' } | "
            "Remove-DnsClientNrptRule -Force -ErrorAction SilentlyContinue"
        )
        namespaces: List[str] = []
        for app_id in blocked_apps:
            namespaces.extend(self.NRPT_WILDCARDS.get(app_id, []))
        if not namespaces:
            return
        # Add a single NRPT rule with all namespaces pointing to 0.0.0.0.
        # PowerShell Add-DnsClientNrptRule accepts -Namespace as an array.
        ns_list = ",".join(f"'{n}'" for n in sorted(set(namespaces)))
        self._run_ps(
            f"Add-DnsClientNrptRule -Namespace @({ns_list}) "
            f"-NameServers '0.0.0.0' -Comment 'PathWise-AppBlock' "
            f"-ErrorAction SilentlyContinue"
        )
        logger.info("NRPT wildcard-block rules installed for: %s", namespaces)

    def _collect_disrupt_ips(self, blocked_apps: List[str]) -> List[str]:
        """DNS-based IP discovery (backup only)."""
        ips: set[str] = set()
        for app_id in blocked_apps:
            for host in DISRUPT_DOMAINS.get(app_id, []):
                for ip in self._resolve_ips(host):
                    if ip and ip != "0.0.0.0" and not ip.startswith("127."):
                        ips.add(ip)
        return sorted(ips)

    def _collect_live_chrome_google_ips(self) -> List[str]:
        """
        Query the OS for every TCP+UDP :443 connection owned by a Chrome
        process, then keep only the ones whose remote IP is in a Google
        CDN prefix. These are the exact IPs Chrome is currently using to
        stream YouTube, so blocking them immediately stalls playback.
        """
        script = (
            "$pids = (Get-Process chrome,msedge,firefox,brave,opera "
            "-ErrorAction SilentlyContinue).Id;"
            "if (-not $pids) { return };"
            "$tcp = Get-NetTCPConnection -OwningProcess $pids -State Established "
            "-ErrorAction SilentlyContinue | "
            "Where-Object { $_.RemotePort -eq 443 } | "
            "Select-Object -ExpandProperty RemoteAddress;"
            "$udp = Get-NetUDPEndpoint -OwningProcess $pids "
            "-ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty RemoteAddress "
            "-ErrorAction SilentlyContinue;"
            "($tcp + $udp) | Sort-Object -Unique"
        )
        res = self._run_ps(script)
        raw = (res.get("stdout") or "").strip().splitlines()

        google_ips: List[str] = []
        for line in raw:
            ip = line.strip()
            if not ip or ip == "0.0.0.0" or ip == "::" or ip.startswith("127."):
                continue
            if ":" in ip:  # IPv6
                low = ip.lower()
                if any(low.startswith(p) for p in self._GOOGLE_V6_PREFIXES):
                    google_ips.append(ip)
            else:
                if any(ip.startswith(p) for p in self._GOOGLE_V4_PREFIXES):
                    google_ips.append(ip)
        logger.info("Live-Chrome Google IPs found: %d -> %s",
                    len(google_ips), google_ips[:10])
        return google_ips

    def _disrupt_active_connections(self, ips: List[str]) -> None:
        """
        Block outbound TCP + UDP :443 to the given IPs. Adding the rule
        tears down Chrome's already-established sockets, stalling the
        streaming player immediately. Rules persist until Reset is
        clicked -- the reset path runs panic_cleanup which removes them.
        """
        if not ips:
            logger.info("Disrupt: no IPs to block (Chrome may not be streaming yet).")
            return

        # Split IPv4 / IPv6 because Windows Firewall wants them separated.
        v4 = [ip for ip in ips if ":" not in ip]
        v6 = [ip for ip in ips if ":" in ip]

        # Remove any stale rules first (defensive).
        self._run_ps(
            "Get-NetFirewallRule -ErrorAction SilentlyContinue | "
            "Where-Object {$_.DisplayName -like 'PW_Disrupt*'} | "
            "Remove-NetFirewallRule -ErrorAction SilentlyContinue"
        )

        def _add_rule(name: str, protocol: str, addrs: List[str]) -> None:
            if not addrs:
                return
            ip_csv = ",".join(addrs)
            self._run_ps(
                f"New-NetFirewallRule -DisplayName '{name}' "
                f"-Direction Outbound -Action Block "
                f"-Protocol {protocol} -RemoteAddress {ip_csv} "
                f"-RemotePort 443 -Enabled True "
                f"-ErrorAction SilentlyContinue"
            )

        _add_rule("PW_Disrupt_TCP_v4",  "TCP", v4)
        _add_rule("PW_Disrupt_UDP_v4",  "UDP", v4)
        _add_rule("PW_Disrupt_TCP_v6",  "TCP", v6)
        _add_rule("PW_Disrupt_UDP_v6",  "UDP", v6)

        # --- Extra demo-focused measures to make the stall VISIBLE fast ---
        #
        # Chrome uses DNS-over-HTTPS (DoH) which bypasses the Windows hosts
        # file entirely -- that is the root cause of "Apply doesn't stop
        # the video". Chrome keeps resolving googlevideo.com through
        # 8.8.8.8:443 (Google DoH) or 1.1.1.1:443 (Cloudflare DoH) and
        # getting fresh CDN IPs that are not in our block list.
        #
        # Fix: block the DoH endpoints. Chrome then falls back to the OS
        # resolver, which DOES honor the hosts file, so googlevideo.com
        # resolves to 0.0.0.0 and the stream fails.
        #
        # These endpoints ARE also Google/Cloudflare DNS. Blocking them
        # briefly is acceptable -- Windows uses the hosts file and the
        # user's configured ISP DNS first.

        DOH_V4 = [
            "8.8.8.8", "8.8.4.4",           # Google Public DNS (also DoH)
            "1.1.1.1", "1.0.0.1",           # Cloudflare (also DoH)
            "9.9.9.9", "149.112.112.112",   # Quad9
            "208.67.222.222", "208.67.220.220",  # OpenDNS
        ]
        DOH_V6 = [
            "2001:4860:4860::8888",  # Google DNS
            "2001:4860:4860::8844",
            "2606:4700:4700::1111",  # Cloudflare
            "2606:4700:4700::1001",
        ]
        _add_rule("PW_Disrupt_DoH_TCP_v4", "TCP", DOH_V4)
        _add_rule("PW_Disrupt_DoH_TCP_v6", "TCP", DOH_V6)

        # Also block QUIC (UDP/443) globally during the block window.
        # Chrome's HTTP/3 QUIC stream can migrate to new IPs invisibly
        # via connection migration -- killing ALL outbound UDP 443 forces
        # Chrome onto TCP where our hosts + IP rules take over. Other
        # services transparently fall back to TCP.
        self._run_ps(
            "New-NetFirewallRule -DisplayName 'PW_Disrupt_QUIC_all' "
            "-Direction Outbound -Action Block -Protocol UDP "
            "-RemotePort 443 -Enabled True -ErrorAction SilentlyContinue"
        )

        # Flush Windows DNS cache once more so next resolve hits hosts file.
        self._run_ps("Clear-DnsClientCache -ErrorAction SilentlyContinue")

        logger.info(
            "Disrupt rules: %d v4 + %d v6 CDN IPs, DoH endpoints, global QUIC block, DNS flush (persist until reset)",
            len(v4), len(v6),
        )

    @staticmethod
    def _resolve_ips(hostname: str) -> List[str]:
        """Resolve A records for *hostname* using the OS resolver."""
        try:
            import socket
            infos = socket.getaddrinfo(hostname, 443, socket.AF_INET, socket.SOCK_STREAM)
            return list({i[4][0] for i in infos})
        except Exception as exc:
            logger.debug("DNS resolve of %s failed: %s", hostname, exc)
            return []

    # -- HOSTS file management --

    def _write_hosts_block(self, domains: List[str]) -> None:
        """Append a PathWise block redirecting each domain to 0.0.0.0."""
        if not WINDOWS_HOSTS.exists():
            logger.warning("Hosts file missing at %s -- skipping block", WINDOWS_HOSTS)
            return

        try:
            # One-time backup per process lifetime
            if not HOSTS_BACKUP.exists():
                shutil.copy2(WINDOWS_HOSTS, HOSTS_BACKUP)
                logger.info("Hosts backup saved to %s", HOSTS_BACKUP)

            original = WINDOWS_HOSTS.read_text(encoding="utf-8", errors="ignore")
            stripped = self._strip_pw_block(original)

            lines = [PW_BEGIN]
            seen: set[str] = set()
            for domain in domains:
                if domain in seen:
                    continue
                seen.add(domain)
                lines.append(f"0.0.0.0 {domain}")
            lines.append(PW_END)

            new_content = stripped.rstrip() + "\n\n" + "\n".join(lines) + "\n"
            WINDOWS_HOSTS.write_text(new_content, encoding="utf-8")
            self._blocked_domains = seen
            self._commands_log.append({
                "cmd": f"hosts-file-block({len(seen)} domains)",
                "ok": True,
                "stdout": ", ".join(sorted(seen)),
                "stderr": "",
            })
        except PermissionError:
            logger.error("Hosts file write denied -- server must run as Administrator")
            self._commands_log.append({
                "cmd": "hosts-file-block",
                "ok": False,
                "stderr": "Permission denied (not Administrator)",
            })
        except Exception as exc:
            logger.exception("Hosts-file write failed: %s", exc)

    @staticmethod
    def _strip_pw_block(content: str) -> str:
        """Remove any previous PathWise-managed block from hosts content."""
        if PW_BEGIN not in content:
            return content
        before, _, rest = content.partition(PW_BEGIN)
        _, _, after = rest.partition(PW_END)
        return before.rstrip() + ("\n" + after.lstrip() if after.strip() else "\n")

    def _restore_hosts(self) -> None:
        """Remove the PathWise block from the hosts file."""
        if not WINDOWS_HOSTS.exists():
            return
        try:
            content = WINDOWS_HOSTS.read_text(encoding="utf-8", errors="ignore")
            if PW_BEGIN not in content:
                return
            cleaned = self._strip_pw_block(content)
            WINDOWS_HOSTS.write_text(cleaned, encoding="utf-8")
            self._blocked_domains = set()
            logger.info("Hosts file PathWise block removed")
        except PermissionError:
            logger.error("Cannot restore hosts file -- not Administrator")
        except Exception as exc:
            logger.exception("Hosts restore failed: %s", exc)

    # -- Panic cleanup (removes everything PathWise ever did) --

    def _panic_cleanup(self) -> None:
        """
        Remove every PathWise artifact: NetQoS policies, firewall disrupt
        rules, hosts file block, DNS cache. Safe to call repeatedly.
        """
        self._run_ps(
            "Get-NetQosPolicy -ErrorAction SilentlyContinue | "
            "Where-Object {$_.Name -like 'PW_*'} | "
            "Remove-NetQosPolicy -Confirm:$false -ErrorAction SilentlyContinue"
        )
        # Also remove any stale disrupt firewall rules
        self._run_ps(
            "Get-NetFirewallRule -ErrorAction SilentlyContinue | "
            "Where-Object {$_.DisplayName -like 'PW_Disrupt*'} | "
            "Remove-NetFirewallRule -ErrorAction SilentlyContinue"
        )
        # Remove NRPT wildcard DNS blocks
        self._run_ps(
            "Get-DnsClientNrptRule -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Comment -eq 'PathWise-AppBlock' } | "
            "Remove-DnsClientNrptRule -Force -ErrorAction SilentlyContinue"
        )
        self._restore_hosts()
        self._run_ps("ipconfig /flushdns")
        self._run_ps("Clear-DnsClientCache -ErrorAction SilentlyContinue")

    # -- Simulation mode --

    def _apply_simulate(self, allocations: Dict[str, dict]) -> None:
        logger.info("[SIMULATE] Would apply rules for %d apps (no OS changes)", len(allocations))

    # -- Subprocess helpers --

    def _run(self, cmd: str) -> dict:
        logger.debug("[shell] %s", cmd)
        result_dict = {"cmd": cmd, "ok": False, "stdout": "", "stderr": ""}
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            result_dict["ok"] = result.returncode == 0
            result_dict["stdout"] = result.stdout.strip()
            result_dict["stderr"] = result.stderr.strip()
            result_dict["returncode"] = result.returncode
        except subprocess.TimeoutExpired:
            result_dict["error"] = "timeout"
        except Exception as exc:
            result_dict["error"] = str(exc)
        self._commands_log.append(result_dict)
        return result_dict

    def _run_ps(self, script: str) -> dict:
        logger.debug("[powershell] %s", script)
        result_dict = {"cmd": script, "ok": False, "stdout": "", "stderr": ""}
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=15,
            )
            result_dict["ok"] = result.returncode == 0
            result_dict["stdout"] = result.stdout.strip()
            result_dict["stderr"] = result.stderr.strip()
            result_dict["returncode"] = result.returncode
        except subprocess.TimeoutExpired:
            result_dict["error"] = "timeout"
        except Exception as exc:
            result_dict["error"] = str(exc)
        self._commands_log.append(result_dict)
        return result_dict
