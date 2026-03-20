#!/usr/bin/env python3
"""
Mininet Validation Server — PathWise AI Digital Twin Sandbox backend.

Listens on TCP port 6000 (configurable via MININET_PORT).
Accepts a JSON topology spec, instantiates a Mininet topology with those
links, runs `pingall` to verify reachability, scans the effective flow graph
for loops, and returns the result as JSON.

Request envelope (one JSON object per line):
  {
    "nodes": [{"id": 1, "name": "fiber-primary"}, ...],
    "links": [{"src": 1, "dst": 2, "bw_mbps": 100, "delay_ms": 5, "loss_pct": 0}, ...],
    "pingall_timeout_s": 3        # optional
  }

Response:
  {
    "passed": bool,
    "checks": [{"name": str, "passed": bool, "detail": str}, ...],
    "elapsed_s": float
  }

Satisfies: Req-Func-Sw-9 (Mininet virtual replica), Req-Qual-Perf-3 (<5s).
"""

from __future__ import annotations
import json
import os
import socket
import socketserver
import sys
import threading
import time
import traceback
from typing import Any


HOST = os.environ.get("MININET_BIND", "0.0.0.0")
PORT = int(os.environ.get("MININET_PORT", "6000"))
PINGALL_TIMEOUT = float(os.environ.get("MININET_PINGALL_TIMEOUT_S", "3"))


def _build_topology(spec: dict):
    """Instantiate a Mininet topology from the JSON spec."""
    from mininet.net import Mininet
    from mininet.node import OVSBridge
    from mininet.link import TCLink

    net = Mininet(switch=OVSBridge, link=TCLink, controller=None,
                  waitConnected=False)

    id_to_switch: dict[Any, Any] = {}
    for node in spec.get("nodes", []):
        sw = net.addSwitch(f"s{node['id']}")
        id_to_switch[node["id"]] = sw

    # One host per switch so pingall has targets to traverse
    hosts = []
    for node in spec.get("nodes", []):
        h = net.addHost(f"h{node['id']}", ip=f"10.0.{int(node['id'])}.1/24")
        net.addLink(h, id_to_switch[node["id"]])
        hosts.append(h)

    for link in spec.get("links", []):
        s, d = id_to_switch[link["src"]], id_to_switch[link["dst"]]
        kwargs = {}
        if "bw_mbps" in link:
            kwargs["bw"] = link["bw_mbps"]
        if "delay_ms" in link:
            kwargs["delay"] = f"{link['delay_ms']}ms"
        if "loss_pct" in link and link["loss_pct"] > 0:
            kwargs["loss"] = link["loss_pct"]
        net.addLink(s, d, **kwargs)

    return net


def _detect_loops(spec: dict) -> tuple[bool, str]:
    """DFS-based undirected cycle detection on the proposed flow graph."""
    adj: dict[str, list[str]] = {}
    for n in spec.get("nodes", []):
        adj[str(n["id"])] = []
    for l in spec.get("links", []):
        s, d = str(l["src"]), str(l["dst"])
        adj.setdefault(s, []).append(d)
        if s != d:
            adj.setdefault(d, []).append(s)

    visited = set()
    on_stack = set()

    def dfs(u: str, parent: str) -> bool:
        visited.add(u)
        on_stack.add(u)
        for v in adj.get(u, []):
            if v == parent:
                continue
            if v not in visited:
                if dfs(v, u):
                    return True
            elif v in on_stack:
                return True
        on_stack.discard(u)
        return False

    for n in adj:
        if n not in visited and dfs(n, ""):
            return True, f"cycle detected starting at node {n}"
    return False, "no cycles detected in proposed flow graph"


def _run_pingall(net) -> tuple[bool, str]:
    """Run pingall and parse the drop percentage."""
    try:
        loss = net.pingAll(timeout=str(PINGALL_TIMEOUT))
        return (loss == 0.0,
                f"pingAll loss={loss:.1f}% (0% means all hosts reachable)")
    except Exception as exc:
        return False, f"pingAll error: {exc}"


def validate(spec: dict) -> dict:
    """Full validation pipeline: loop detection + Mininet pingAll."""
    t0 = time.perf_counter()
    checks = []

    loop_found, loop_detail = _detect_loops(spec)
    checks.append({
        "name": "loop_detection",
        "passed": not loop_found,
        "detail": loop_detail,
    })
    if loop_found:
        return {"passed": False, "checks": checks,
                "elapsed_s": round(time.perf_counter() - t0, 3)}

    # Only spin up Mininet if the graph is loop-free (cheap guard)
    try:
        from mininet.log import setLogLevel
        setLogLevel("error")
    except Exception:
        pass

    net = None
    try:
        net = _build_topology(spec)
        net.start()
        reachable, reach_detail = _run_pingall(net)
        checks.append({
            "name": "reachability_mininet",
            "passed": reachable,
            "detail": reach_detail,
        })
    except Exception as exc:
        checks.append({
            "name": "reachability_mininet",
            "passed": False,
            "detail": f"mininet error: {exc}",
        })
    finally:
        if net is not None:
            try:
                net.stop()
            except Exception:
                pass

    overall_passed = all(c["passed"] for c in checks)
    return {
        "passed": overall_passed,
        "checks": checks,
        "elapsed_s": round(time.perf_counter() - t0, 3),
    }


class ValidationHandler(socketserver.StreamRequestHandler):
    """Reads one JSON spec per line, writes one JSON response per line."""

    def handle(self):
        peer = self.client_address
        try:
            raw = self.rfile.readline()
            if not raw:
                return
            spec = json.loads(raw.decode("utf-8"))
            result = validate(spec)
        except Exception:
            result = {
                "passed": False,
                "checks": [{
                    "name": "parse_error",
                    "passed": False,
                    "detail": traceback.format_exc(),
                }],
                "elapsed_s": 0,
            }
        payload = (json.dumps(result) + "\n").encode("utf-8")
        try:
            self.wfile.write(payload)
        except Exception:
            pass
        print(f"[mininet-validator] {peer} passed={result.get('passed')} "
              f"elapsed={result.get('elapsed_s')}s",
              file=sys.stderr, flush=True)


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    # Mininet needs root. If we're not root, print a clear error.
    if os.geteuid() != 0 and sys.platform != "win32":
        print("mininet requires root — re-run with sudo or inside privileged container",
              file=sys.stderr)
        sys.exit(2)

    print(f"[mininet-validator] listening on {HOST}:{PORT}", flush=True)
    with ThreadingTCPServer((HOST, PORT), ValidationHandler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[mininet-validator] shutting down", flush=True)


if __name__ == "__main__":
    main()
