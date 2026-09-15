from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from tools._shared import ROOT, err


ASSET_FILE = ROOT / "helpdesk_data" / "assets.json"

# Mock internal network database for Northstar Labs IT Helpdesk
NETWORK_TOPOLOGY = {
    # Internal servers & services
    "gateway.northstar.internal": {
        "ip": "10.0.0.1",
        "avg_latency_ms": 2.1,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [80, 443, 22],
        "status": "healthy",
        "hops": ["10.0.0.1"],
    },
    "dns.northstar.internal": {
        "ip": "10.0.0.2",
        "avg_latency_ms": 1.5,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [53, 22],
        "status": "healthy",
        "hops": ["10.0.0.1", "10.0.0.2"],
    },
    "sso.northstar.internal": {
        "ip": "10.0.1.10",
        "avg_latency_ms": 5.4,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [80, 443],
        "status": "healthy",
        "hops": ["10.0.0.1", "10.0.1.1", "10.0.1.10"],
    },
    "vpn.northstar.internal": {
        "ip": "10.0.1.20",
        "avg_latency_ms": 14.8,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [443, 1194],
        "status": "healthy",
        "hops": ["10.0.0.1", "10.0.1.1", "10.0.1.20"],
    },
    "mail.northstar.internal": {
        "ip": "10.0.1.30",
        "avg_latency_ms": 7.2,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [25, 443, 587, 993],
        "status": "healthy",
        "hops": ["10.0.0.1", "10.0.1.1", "10.0.1.30"],
    },
    "intranet.northstar.internal": {
        "ip": "10.0.2.10",
        "avg_latency_ms": 4.1,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [80, 443],
        "status": "healthy",
        "hops": ["10.0.0.1", "10.0.2.1", "10.0.2.10"],
    },
    "backup.northstar.internal": {
        "ip": "10.0.2.50",
        "avg_latency_ms": 320.0,
        "packet_loss_pct": 25.0,
        "dns_resolved": True,
        "open_ports": [22, 873],
        "status": "degraded",
        "hops": ["10.0.0.1", "10.0.2.1", "10.0.2.50"],
    },
    "printer-floor4.northstar.internal": {
        "ip": "10.0.4.15",
        "avg_latency_ms": 0.0,
        "packet_loss_pct": 100.0,
        "dns_resolved": True,
        "open_ports": [],
        "status": "unreachable",
        "hops": ["10.0.0.1", "* * * Request timed out"],
    },
    # Common IPs and external targets
    "10.0.0.1": {
        "ip": "10.0.0.1",
        "hostname": "gateway.northstar.internal",
        "avg_latency_ms": 2.1,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [80, 443, 22],
        "status": "healthy",
        "hops": ["10.0.0.1"],
    },
    "192.168.1.1": {
        "ip": "192.168.1.1",
        "hostname": "local-gateway",
        "avg_latency_ms": 1.2,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [80, 443, 53],
        "status": "healthy",
        "hops": ["192.168.1.1"],
    },
    "8.8.8.8": {
        "ip": "8.8.8.8",
        "hostname": "dns.google",
        "avg_latency_ms": 22.4,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [53, 443],
        "status": "healthy",
        "hops": ["10.0.0.1", "198.51.100.1", "8.8.8.8"],
    },
    "1.1.1.1": {
        "ip": "1.1.1.1",
        "hostname": "one.one.one.one",
        "avg_latency_ms": 18.2,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [53, 443, 853],
        "status": "healthy",
        "hops": ["10.0.0.1", "198.51.100.1", "1.1.1.1"],
    },
    "google.com": {
        "ip": "142.250.190.46",
        "avg_latency_ms": 25.0,
        "packet_loss_pct": 0.0,
        "dns_resolved": True,
        "open_ports": [80, 443],
        "status": "healthy",
        "hops": ["10.0.0.1", "198.51.100.1", "142.250.190.46"],
    },
}


def _lookup_asset_network(asset_id: str) -> dict[str, Any] | None:
    try:
        if not ASSET_FILE.exists():
            return None
        data = json.loads(ASSET_FILE.read_text(encoding="utf-8"))
        asset = next((a for a in data.get("assets", []) if a["asset_id"].upper() == asset_id.upper()), None)
        if not asset:
            return None
        diag = asset.get("diagnostics", {})
        net_info = diag.get("network", "")
        # Parse simulated latency/status from asset network diagnostics
        is_online = "online" in net_info.lower()
        return {
            "asset_id": asset["asset_id"],
            "model": asset.get("model", ""),
            "location": asset.get("location", ""),
            "network_diagnostics_raw": net_info,
            "status": "healthy" if is_online else "degraded",
            "is_online": is_online,
        }
    except Exception:
        return None


def network_diagnostic(
    target: str = "",
    test_type: str = "ping",
    port: int | None = None,
    count: int = 3,
) -> dict[str, Any]:
    """Execute network diagnostic tests against an IP, hostname, domain, or device asset."""
    try:
        target_clean = (target or "").strip()
        if not target_clean:
            return {
                "tool": "network_diagnostic",
                "error": "missing_target",
                "message": "Target (IP address, hostname, domain, or asset_id) is required for network diagnostic.",
            }

        wanted_type = (test_type or "ping").strip().lower()
        valid_types = {"ping", "dns", "port", "traceroute", "full", "all"}
        if wanted_type not in valid_types:
            wanted_type = "ping"

        now_iso = datetime.now(timezone.utc).isoformat()
        target_lower = target_clean.lower()

        # Check if target is an internal asset ID (e.g. LT-204, DT-031)
        if target_clean.upper().startswith(("LT-", "DT-", "PR-", "SRV-")):
            asset_net = _lookup_asset_network(target_clean)
            if asset_net:
                return {
                    "tool": "network_diagnostic",
                    "target": target_clean.upper(),
                    "target_type": "asset_device",
                    "test_type": wanted_type,
                    "status": asset_net["status"],
                    "asset_info": {
                        "asset_id": asset_net["asset_id"],
                        "model": asset_net["model"],
                        "location": asset_net["location"],
                    },
                    "network_summary": asset_net["network_diagnostics_raw"],
                    "timestamp": now_iso,
                }

        # Check against mock topology
        node = NETWORK_TOPOLOGY.get(target_lower)
        if not node:
            # Check IP match
            for k, v in NETWORK_TOPOLOGY.items():
                if v.get("ip") == target_lower:
                    node = v
                    break

        if not node:
            # If target ends with .northstar.internal or looks like an unlisted host
            if target_lower.endswith(".northstar.internal") or target_lower.startswith("10.0."):
                return {
                    "tool": "network_diagnostic",
                    "target": target_clean,
                    "target_type": "internal_host",
                    "test_type": wanted_type,
                    "status": "unreachable",
                    "error": "host_unreachable",
                    "message": f"Host '{target_clean}' could not be reached on the internal Northstar network.",
                    "packet_loss_pct": 100.0,
                    "timestamp": now_iso,
                }
            else:
                # Default generic external/local simulation
                node = {
                    "ip": target_clean if any(c.isdigit() for c in target_clean) else "93.184.216.34",
                    "avg_latency_ms": 35.0,
                    "packet_loss_pct": 0.0,
                    "dns_resolved": True,
                    "open_ports": [80, 443],
                    "status": "healthy",
                    "hops": ["10.0.0.1", "198.51.100.1", target_clean],
                }

        # Build response based on test_type
        result: dict[str, Any] = {
            "tool": "network_diagnostic",
            "target": target_clean,
            "target_ip": node.get("ip", "unknown"),
            "test_type": wanted_type,
            "status": node.get("status", "healthy"),
            "timestamp": now_iso,
        }

        # Ping metrics
        if wanted_type in {"ping", "full", "all"}:
            loss = node.get("packet_loss_pct", 0.0)
            latency = node.get("avg_latency_ms", 0.0)
            result["ping_results"] = {
                "packets_transmitted": count,
                "packets_received": int(count * (1 - loss / 100.0)),
                "packet_loss_pct": loss,
                "avg_latency_ms": latency,
                "min_latency_ms": round(max(0.5, latency * 0.85), 2) if latency > 0 else 0,
                "max_latency_ms": round(latency * 1.25, 2) if latency > 0 else 0,
                "reachable": loss < 100.0,
            }

        # DNS lookup
        if wanted_type in {"dns", "full", "all"}:
            dns_ok = node.get("dns_resolved", True)
            result["dns_lookup"] = {
                "query": target_clean,
                "resolved_ip": node.get("ip"),
                "authoritative_dns": "10.0.0.2 (dns.northstar.internal)",
                "dns_status": "NOERROR" if dns_ok else "NXDOMAIN",
            }

        # Port reachability check
        if wanted_type in {"port", "full", "all"} or port is not None:
            check_port = port if port is not None else 443
            open_ports = node.get("open_ports", [])
            is_open = check_port in open_ports
            result["port_check"] = {
                "port": check_port,
                "status": "OPEN" if is_open else "CLOSED_OR_FILTERED",
                "open_ports_detected": open_ports,
            }

        # Traceroute
        if wanted_type in {"traceroute", "full", "all"}:
            result["traceroute"] = {
                "hops": node.get("hops", ["10.0.0.1", target_clean]),
                "hop_count": len(node.get("hops", [])),
                "completed": node.get("status") != "unreachable",
            }

        return result

    except Exception as exc:
        return err("network_diagnostic", exc)
