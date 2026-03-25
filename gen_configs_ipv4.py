#!/usr/bin/env python3
# Script de génération automatique de configurations IPv4
# - IGP: OSPF dans le core
# - eBGP entre PE et CE
# - MPLS LDP dans le core (sauf interfaces PE vers CE)
# - Loopbacks /32 pour OSPF et BGP

import json
import os
import ipaddress


# =========================
# Utilitaires / Validation
# =========================

def ensure(cond, msg):
    if not cond:
        raise SystemExit(f"[ERROR] {msg}")


def ip_no_prefix(addr):
    return addr.split("/")[0].strip()


def cidr_to_ip_and_mask(cidr: str):
    """Return (ip, netmask) for a CIDR string like '10.0.0.1/24' or '10.0.0.4/32'."""
    iface = ipaddress.ip_interface(cidr)
    return str(iface.ip), str(iface.network.netmask)


# =========================
# Allocation des adresses
# =========================

def allocate_loopbacks(intent):
    """Allocate /32 loopback addresses from pools"""
    out = {}
    for asn, asdata in intent["ases"].items():
        pool_str = asdata["ip_pools"]["loopbacks"]
        pool = ipaddress.IPv4Network(pool_str)
        base = pool.network_address

        routers = asdata.get("routers", [])
        ensure(routers, f"AS {asn} must define routers list")

        for idx, rname in enumerate(routers, start=1):
            out[rname] = f"{base + idx}/32"
    return out


def allocate_link_ips(intent):
    """Allocate /24 link addresses from link definitions"""
    out = {}
    for link in intent["links"]:
        name = link.get("name", "<unnamed>")
        subnet_str = link.get("subnet")
        ensure(subnet_str, f"Link {name} missing subnet")

        net = ipaddress.IPv4Network(subnet_str)
        ensure(net.prefixlen == 24, f"Link {name} subnet must be /24, got /{net.prefixlen}")

        eps = link.get("endpoints", [])
        ensure(len(eps) == 2, f"Link {name} must have exactly 2 endpoints")

        r0, i0 = eps[0]["router"], eps[0]["interface"]
        r1, i1 = eps[1]["router"], eps[1]["interface"]

        ensure((r0, i0) not in out, f"Interface reused: {r0}:{i0}")
        ensure((r1, i1) not in out, f"Interface reused: {r1}:{i1}")

        # .1 is network, .2 and .3 are usable IPs
        out[(r0, i0)] = f"{net.network_address + 1}/24"
        out[(r1, i1)] = f"{net.network_address + 2}/24"

    return out


def adjacency(intent):
    """Build adjacency list: router -> list of links"""
    adj = {}
    for link in intent["links"]:
        for ep in link["endpoints"]:
            adj.setdefault(ep["router"], []).append(link)
    return adj


def get_endpoint_for_router(link, rname):
    eps = link["endpoints"]
    if eps[0]["router"] == rname:
        return eps[0]
    if eps[1]["router"] == rname:
        return eps[1]
    raise SystemExit(f"[ERROR] Router {rname} not in {link.get('name','<unnamed>')}")


def other_endpoint(link, rname):
    eps = link["endpoints"]
    if eps[0]["router"] == rname:
        return eps[1]
    if eps[1]["router"] == rname:
        return eps[0]
    raise SystemExit(f"[ERROR] Router {rname} not in {link.get('name','<unnamed>')}")


# =========================
# VRF Helper Functions
# =========================

def find_vrf_for_ce(intent, ce_router):
    """Find VRF config for a CE router.
    Returns: (vrf_name, rd, rt) or (None, None, None) if not found
    """
    vrf_config = intent.get("vrf", {})
    for vrf_name, vrf_data in vrf_config.items():
        for member in vrf_data.get("members", []):
            if member["ce"] == ce_router:
                return vrf_name, member["rd"], vrf_data["rt"]
    return None, None, None


def get_ce_for_inter_as_link(link, pe_router):
    """For an inter_as link and a PE router on that link,
    return the CE router endpoint and its data.
    """
    eps = link["endpoints"]
    if eps[0]["router"] == pe_router:
        ce = eps[1]["router"]
    elif eps[1]["router"] == pe_router:
        ce = eps[0]["router"]
    else:
        return None, None
    return ce


def build_vrf_config_for_pe(intent, pe_router, adj):
    """Generate VRF configuration for a PE router."""
    lines = []
    vrf_config = intent.get("vrf", {})
    
    if not vrf_config:
        return lines
    
    # Track which VRFs we've already created
    vrfs_created = set()
    
    # First pass: identify all VRFs needed by this PE
    for link in adj.get(pe_router, []):
        if link.get("type") != "inter_as":
            continue
        ce = get_ce_for_inter_as_link(link, pe_router)
        if not ce:
            continue
        vrf_name, rd, rt = find_vrf_for_ce(intent, ce)
        if vrf_name and vrf_name not in vrfs_created:
            vrfs_created.add(vrf_name)
            lines.extend([
                f"ip vrf {vrf_name}",
                f" rd {rd}",
                f" route-target export {rt}",
                f" route-target import {rt}",
                "exit",
                "!"
            ])
    
    return lines


# =========================
# OSPF Generation
# =========================

def ospf_global(asdata, router_id, process_id):
    """Generate global OSPF configuration"""
    lines = [
        f"router ospf {process_id}",
        f" router-id {router_id}",
        " log-adjacency-changes",
        "exit",
        "!"
    ]
    return lines


def ospf_iface_lines(link_type):
    """Generate OSPF interface commands"""
    if link_type == "intra_as":
        return [
            " ip ospf 1 area 0",
        ]
    return []


# =========================
# MPLS LDP Generation
# =========================

def mpls_global(asdata):
    """Generate global MPLS/LDP configuration"""
    lines = [
        "mpls ip",
        "!",
        "mpls ldp router-id Loopback0 force",
        "!"
    ]
    return lines


def mpls_iface_lines(link_type, router_role):
    """Generate MPLS/LDP interface commands"""
    # MPLS LDP only on intra_as links
    # For PE routers: not on interface toward CE (inter_as)
    if link_type == "intra_as":
        return [
            " mpls ip",
        ]
    elif link_type == "inter_as" and router_role == "PE":
        # Don't enable MPLS on this interface (CE facing)
        return []
    return []


# =========================
# BGP Generation
# =========================

def has_ebgp_neighbor(intent, rname):
    """Check if router has inter_as neighbors"""
    for link in intent["links"]:
        if link.get("type") != "inter_as":
            continue
        eps = link["endpoints"]
        if eps[0]["router"] == rname or eps[1]["router"] == rname:
            return True
    return False


def build_bgp(intent, rname, loopbacks, link_ips, adj):
    """Generate BGP configuration"""
    if not intent.get("bgp", {}).get("required", False):
        return []

    routers = intent["routers"]
    ases = intent["ases"]

    my_asn = int(routers[rname]["as"])
    my_role = routers[rname].get("role", "")
    rid = routers[rname]["router_id"]

    lines = [
        f"router bgp {my_asn}",
        f" bgp router-id {rid}",
        " bgp log-neighbor-changes",
        " no auto-summary",
        " no synchronization",
    ]

    # ---- iBGP configuration (Route Reflector or Full Mesh)
    bgp_config = intent.get("bgp", {}).get("ibgp", {})
    bgp_mode = bgp_config.get("mode", "full_mesh")
    
    ibgp_peers = []
    
    if bgp_mode == "route_reflector":
        rr_router = bgp_config.get("route_reflector")
        clients = bgp_config.get("clients", [])
        
        if rname == rr_router:
            # I'm the Route Reflector
            # Peer with all clients
            for client in clients:
                client_lb = ip_no_prefix(loopbacks[client])
                lines.append(f" neighbor {client_lb} remote-as {my_asn}")
                lines.append(f" neighbor {client_lb} update-source Loopback0")
                lines.append(f" neighbor {client_lb} route-reflector-client")
                ibgp_peers.append(client_lb)
            
            # Add cluster-id (using RR's router-id)
            lines.append(f" bgp cluster-id {rid}")
        
        elif rname in clients:
            # I'm a client, peer with the RR
            rr_lb = ip_no_prefix(loopbacks[rr_router])
            lines.append(f" neighbor {rr_lb} remote-as {my_asn}")
            lines.append(f" neighbor {rr_lb} update-source Loopback0")
            ibgp_peers.append(rr_lb)
    
    else:  # full_mesh mode (default)
        # Original full mesh behavior for PE routers in same AS
        for peer in ases[str(my_asn)]["routers"]:
            if peer == rname:
                continue
            peer_role = routers[peer].get("role", "")
            # For MPLS, we need iBGP between PE/P routers that have BGP
            if my_role in ["PE", "P"] and peer_role in ["PE", "P"]:
                peer_lb = ip_no_prefix(loopbacks[peer])
                ibgp_peers.append(peer_lb)
                lines.append(f" neighbor {peer_lb} remote-as {my_asn}")
                lines.append(f" neighbor {peer_lb} update-source Loopback0")

    # ---- eBGP neighbors (inter_as) - organized by VRF for PEs
    ebgp_peers = []  # list of (peer_ip, peer_asn, peer_router, vrf_name)
    ebgp_by_vrf = {}  # maps vrf_name -> [(peer_ip, peer_asn, peer_router), ...]
    
    for link in adj.get(rname, []):
        if link.get("type") != "inter_as":
            continue

        other = other_endpoint(link, rname)
        peer_router = other["router"]
        peer_asn = int(routers[peer_router]["as"])
        peer_ip = ip_no_prefix(link_ips[(peer_router, other["interface"])])

        if peer_ip in [p[0] for p in ebgp_peers]:
            continue

        # Determine VRF for this eBGP neighbor
        vrf_name = None
        if my_role == "PE":
            vrf_name, rd, rt = find_vrf_for_ce(intent, peer_router)
        
        # For PE with VRF: declare neighbor inside address-family, not globally
        if not vrf_name:
            lines.append(f" neighbor {peer_ip} remote-as {peer_asn}")
        
        ebgp_peers.append((peer_ip, peer_asn, peer_router, vrf_name))
        
        # Track by VRF
        if vrf_name:
            ebgp_by_vrf.setdefault(vrf_name, []).append((peer_ip, peer_asn, peer_router))

    # ---- Address Families
    lines.append(" !")
    
    # For PE routers: VPNv4 address family for iBGP
    if my_role == "PE" and ibgp_peers:
        lines += [
            " address-family vpnv4",
        ]
        for peer_lb in ibgp_peers:
            lines.append(f"  neighbor {peer_lb} activate")
            lines.append(f"  neighbor {peer_lb} send-community extended")
        lines += [
            " exit-address-family",
            "!",
        ]
    
    # For P/RR routers: VPNv4 address family for iBGP
    if my_role == "P" and ibgp_peers:
        lines += [
            " address-family vpnv4",
        ]
        for peer_lb in ibgp_peers:
            lines.append(f"  neighbor {peer_lb} activate")
            lines.append(f"  neighbor {peer_lb} send-community extended")
            # If this router is route-reflector, also mark clients in vpnv4
            if bgp_mode == "route_reflector" and rname == bgp_config.get("route_reflector"):
                lines.append(f"  neighbor {peer_lb} route-reflector-client")
        lines += [
            " exit-address-family",
            "!",
        ]
    
    # For PE routers: VRF-specific address families for eBGP
    if my_role == "PE" and ebgp_by_vrf:
        for vrf_name in sorted(ebgp_by_vrf.keys()):
            lines += [
                f" address-family ipv4 vrf {vrf_name}",
                "  redistribute connected",
            ]
            peers_in_vrf = ebgp_by_vrf[vrf_name]
            for peer_ip, peer_asn, _ in peers_in_vrf:
                lines.append(f"  neighbor {peer_ip} remote-as {peer_asn}")
                lines.append(f"  neighbor {peer_ip} activate")
            
            lines += [
                " exit-address-family",
                "!",
            ]
    elif my_role == "CE":
        # For CE routers: standard IPv4 address family
        lines += [
            " address-family ipv4",
        ]
        for peer_ip, _, _, _ in ebgp_peers:
            lines.append(f"  neighbor {peer_ip} activate")
        
        # Announce CE loopback
        net = ipaddress.ip_network(loopbacks[rname], strict=False)
        lines.append(f"  network {net.network_address} mask {net.netmask}")
        
        lines += [
            " exit-address-family",
        ]
    elif my_role == "P" and ebgp_peers:
        # For P routers: standard IPv4 address family (if they have eBGP)
        lines += [
            " address-family ipv4",
        ]
        for peer_ip, _, _, _ in ebgp_peers:
            lines.append(f"  neighbor {peer_ip} activate")
        lines += [
            " exit-address-family",
        ]
    
    lines += [
        "exit",
        "!"
    ]
    return lines


# =========================
# Router Configuration
# =========================

def build_router_config(intent, rname, loopbacks, link_ips, adj, enable_secret=None):
    """Build complete router configuration"""
    routers = intent["routers"]
    ases = intent["ases"]

    asn = routers[rname]["as"]
    asdata = ases[str(asn)]
    role = routers[rname].get("role", "")

    lines = [
        "!",
        "enable",
        f"hostname {rname}",
        "!",
        "no ip domain-lookup",
        "ip routing",
    ]

    if enable_secret:
        lines.append(f"enable secret {enable_secret}")

    lines += ["!"]

    # Loopback0
    ip_lb, mask_lb = cidr_to_ip_and_mask(loopbacks[rname])
    lines += [
        "interface Loopback0",
        f" ip address {ip_lb} {mask_lb}",
    ]
    # Add Loopback0 to OSPF for core routers (PE/P) so iBGP sessions can establish
    if asdata["igp"]["type"] == "ospf" and role in ["PE", "P"]:
        lines.append(" ip ospf 1 area 0")
    lines += [" no shutdown", "exit", "!"]

    # VRF configuration (if PE router)
    if role == "PE":
        lines += build_vrf_config_for_pe(intent, rname, adj)

    # Physical interfaces
    for link in adj.get(rname, []):
        my_ep = get_endpoint_for_router(link, rname)
        iface = my_ep["interface"]
        ip = link_ips[(rname, iface)]
        ip_if, ip_mask = cidr_to_ip_and_mask(ip)
        link_type = link.get("type", "intra_as")

        lines += [
            f"interface {iface}",
        ]

        # For inter_as links on PE routers, assign to VRF
        if link_type == "inter_as" and role == "PE":
            ce = get_ce_for_inter_as_link(link, rname)
            if ce:
                vrf_name, _, _ = find_vrf_for_ce(intent, ce)
                if vrf_name:
                    lines.append(f" ip vrf forwarding {vrf_name}")

        lines.append(f" ip address {ip_if} {ip_mask}")

        # OSPF on intra_as links
        if link_type == "intra_as":
            lines += ospf_iface_lines(link_type)

        # MPLS on intra_as links (and on PE inter_as if needed)
        lines += mpls_iface_lines(link_type, role)

        lines += [" no shutdown", "exit", "!"]

    # OSPF configuration (if core router)
    if asdata["igp"]["type"] == "ospf":
        process_id = asdata["igp"]["process_id"]
        router_id = routers[rname]["router_id"]
        lines += ospf_global(asdata, router_id, process_id)

    # MPLS global configuration (if core router)
    if role in ["PE", "P"]:
        lines += mpls_global(asdata)

    # BGP configuration
    lines += build_bgp(intent, rname, loopbacks, link_ips, adj)

    lines += ["end", "!"]
    return "\n".join(lines) + "\n"


# =========================
# Main
# =========================

def main():
    intent_path = os.environ.get("INTENT_PATH", "intents/intent_big_ipv4.json")
    out_dir = os.environ.get("OUT_DIR", "configs_big_gen")

    enable_secret = os.environ.get("ENABLE_SECRET", None)

    ensure(os.path.isfile(intent_path), f"Intent file not found: {intent_path}")

    with open(intent_path, "r", encoding="utf-8") as f:
        intent = json.load(f)

    loopbacks = allocate_loopbacks(intent)
    link_ips = allocate_link_ips(intent)
    adj = adjacency(intent)

    os.makedirs(out_dir, exist_ok=True)

    for rname in intent["routers"].keys():
        cfg = build_router_config(intent, rname, loopbacks, link_ips, adj, enable_secret=enable_secret)
        with open(os.path.join(out_dir, f"{rname}.cfg"), "w", encoding="utf-8") as f:
            f.write(cfg)

    print(f"[OK] Generated IPv4 configs in {out_dir}/")
    print(f"[OK] Loopbacks allocation:")
    for r, lb in sorted(loopbacks.items()):
        print(f"      {r}: {lb}")


if __name__ == "__main__":
    main()
