#!/usr/bin/env python3
import sys
import re
import json
import time
import argparse

try:
    import bluetooth  # PyBluez
except ImportError:
    print("[-] PyBluez (bluetooth) not found. Install with: pip install pybluez")
    sys.exit(1)

from modules.construct_sm import construct_sm
from modules.mutation import fuzz_rfcomm
from modules.service_exerciser import service_exerciser



# ---------- UI Helpers ----------

def _print_rule():
    print("-" * 83)

def _fmt(s, width):
    """Safe left-clip + pad for fixed-width columns."""
    s = "" if s is None else str(s)
    return s[:width].ljust(width)

def _is_mac(s):
    return bool(re.fullmatch(r"(?i)([0-9A-F]{2}:){5}[0-9A-F]{2}", s or ""))

def _profile_id_str(serv):
    """
    Return a normalized string for the first profile UUID:
    - Accepts int (format 0xNNNN)
    - Accepts hex string like "0x110E"
    - Falls back to string/Unknown gracefully
    """
    try:
        profs = serv.get("profiles") or []
        if not profs:
            return "Unknown"
        first = profs[0]
        # PyBluez usually gives tuples like (uuid, version)
        if isinstance(first, (list, tuple)) and first:
            val = first[0]
        else:
            val = first
        # Normalize bytes -> str
        if isinstance(val, (bytes, bytearray)):
            try:
                val = val.decode("ascii", "ignore")
            except Exception:
                val = str(val)
        # If it's a string that looks like hex, normalize
        if isinstance(val, str):
            v = val.strip()
            if v.lower().startswith("0x"):
                try:
                    return f"0x{int(v, 16):04X}"
                except Exception:
                    return v
            return v if v else "Unknown"
        # If it's an int, format as hex
        if isinstance(val, int):
            return f"0x{val:04X}"
        # Fallback
        return str(val)
    except Exception:
        return "Unknown"


# ---------- Device Discovery (used when --ba is omitted) ----------

def discover_device_interactive(scan_secs=3):
    """
    Scan for nearby Bluetooth devices and let the user pick one, or provide a MAC.
    Returns a MAC address string or None.
    """
    while True:
        print("[1/3] DEVICE DISCOVERY")
        print(f"[*] Scanning for Bluetooth devices... ({scan_secs}s)")
        try:
            devices = bluetooth.discover_devices(
                duration=scan_secs, lookup_names=True, flush_cache=True
            )
        except Exception as e:
            print(f"[-] Device discovery failed: {e}")
            devices = []

        print(f"[+] Found {len(devices)} device(s)")
        if devices:
            print("  [#]  [Name]                         [MAC]")
            for i, (addr, name) in enumerate(devices):
                name = name or "Unknown"
                print(f"  {i:02d}. {_fmt(name, 30)} {_fmt(addr, 17)}")
        _print_rule()

        choice = input("[Q] Select device index, or (r)escan / (m)anual MAC / (q)uit: ").strip().lower()

        if choice == "q":
            return None
        if choice == "r":
            print()
            continue
        if choice == "m":
            mac = input("[?] Enter target MAC (e.g., 01:23:45:67:89:AB): ").strip()
            if _is_mac(mac):
                return mac.upper()
            print("[-] Not a valid MAC. Try again.\n")
            continue

        # index
        try:
            idx = int(choice)
            if 0 <= idx < len(devices):
                return devices[idx][0].upper()
            print("[-] Index out of range.\n")
        except ValueError:
            print("[-] Invalid input. Enter a number, r, m, or q.\n")


# ---------- Service Discovery & Selection ----------

def find_services_for_addr(addr):
    try:
        return bluetooth.find_service(address=addr) or []
    except bluetooth.btcommon.BluetoothError as e:
        print(f"[-] Service discovery failed: {e}")
        return []

def pick_rfcomm_services_interactive(addr):
    """
    Show all services; then show RFCOMM-only view where the user can pick one or 'all'.
    Returns a list of selected RFCOMM service dicts.
    """
    print("[2/3] SELECTING RFCOMM SERVICE")
    services = find_services_for_addr(addr)

    print(f"[+] Found {len(services)} profile(s) in the device")
    # Full view (all protocols)
    print("  [#]  [Service Name]                 [Protocol]   [Port]       [ID]        ")
    for i, serv in enumerate(services):
        name = serv.get("name")
        if isinstance(name, bytes):
            name = name.decode("utf-8", "ignore")
        name = name or "Unknown"
        proto = (serv.get("protocol") or "Unknown").upper()
        port = serv.get("port")
        port_str = str(port) if port is not None else "N/A"
        prof_id = _profile_id_str(serv)
        print(f"  {i:02d}. {_fmt(name, 30)} {_fmt(proto, 12)} {_fmt(port_str, 12)} {_fmt(prof_id, 10)}")
    _print_rule()

    # RFCOMM-only filtered list
    rfcomm_services = [
        s for s in services if (s.get("protocol") or "").upper() == "RFCOMM" and isinstance(s.get("port"), int)
    ]

    if not rfcomm_services:
        print("[-] This device exposes no RFCOMM services. Nothing to fuzz.")
        return []

    print("[?] Select an RFCOMM service to fuzz, or type 'all' for every RFCOMM port.")
    print("  [#]  [Service Name]                 [Protocol]   [Port]     [ID]      ")
    for i, serv in enumerate(rfcomm_services):
        name = serv.get("name")
        if isinstance(name, bytes):
            name = name.decode("utf-8", "ignore")
        name = name or "Unknown"
        proto = (serv.get("protocol") or "Unknown").upper()
        port = serv.get("port")
        prof_id = _profile_id_str(serv)
        print(f"  {i:02d}. {_fmt(name, 30)} {_fmt(proto, 10)} {_fmt(port, 8)} {_fmt(prof_id, 8)}")
    _print_rule()

    while True:
        sel = input("[Q] Index or 'all': ").strip().lower()
        if sel == "all":
            return rfcomm_services
        try:
            idx = int(sel)
            if 0 <= idx < len(rfcomm_services):
                return [rfcomm_services[idx]]
            print("[-] Index out of range.")
        except ValueError:
            print("[-] Invalid input. Enter an index or 'all'.")


# ---------- Main ----------

def build_and_visualize_sm(target_addr, selected_services, visualize=True, vis_path="rfcomm_fsm.png"):
    # Build the DLCI list from selected RFCOMM services
    target_dlcis = sorted({
        s.get("port")
        for s in selected_services
        if (s.get("protocol") or "").upper() == "RFCOMM" and isinstance(s.get("port"), int)
    })

    if not target_dlcis:
        print("[-] No RFCOMM channels were selected/found. Aborting.")
        sys.exit(1)

    # Summary (mirrors the original style)
    print("===================TEST PLAN SUMMARY===================")
    print(json.dumps({
        "tool_name": "b2fuzz",
        "interface": "Bluetooth",
        "toolVer": "1.0.0",
        "protocol": "RFCOMM",
        "bdaddr": target_addr,
        "service": "RFCOMM",
        "port": target_dlcis[-1] if len(target_dlcis) == 1 else None
    }, indent=2))
    print(f"Will test the following RFCOMM channels: {target_dlcis}")
    print("======================================================")

    # Build the state machine across those DLCIs
    print("[3/3] BUILDING RFCOMM STATE MACHINE")
    machine = construct_sm(
        target_addr,
        target_channels=target_dlcis,
        VISUALIZE=visualize,
        vis_path=vis_path
    )

    if machine is None:
        print("[-] Failed to build the state machine.")
        sys.exit(1)

    return machine, target_dlcis


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="B2fuzz RFCOMM driver")
    p.add_argument("--layer", default="RFCOMM", help="Protocol layer (default: RFCOMM)")
    p.add_argument("--ba", dest="target_addr", help="Bluetooth MAC address (e.g., 01:23:45:67:89:AB)")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose")
    p.add_argument("--fuzz", action="store_true", help="Start fuzzing after building the state machine")
    p.add_argument("--time", type=int, help="Total fuzzing time in seconds (split across CTRL + DLCIs)")
    p.add_argument("--timeretry", action="store_true", help="Keep retrying within each time slice")
    p.add_argument("--scan-secs", type=int, default=3, help="Discovery scan seconds when --ba is omitted (default: 3)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if (args.layer or "").upper() != "RFCOMM":
        print("[-] Only RFCOMM is supported by this entrypoint.")
        sys.exit(1)

    # Resolve target address: either from CLI or discover interactively
    target_addr = args.target_addr.upper() if args.target_addr else None
    if not target_addr:
        target_addr = discover_device_interactive(scan_secs=args.scan_secs)
        if not target_addr:
            print("[-] No target selected.")
            sys.exit(1)
        print(f"[+] Selected target: {target_addr}")

    # Service discovery & RFCOMM selection
    selected_services = pick_rfcomm_services_interactive(target_addr)
    if not selected_services:
        sys.exit(1)

    # Build SM (and save viz)
    machine, target_dlcis = build_and_visualize_sm(
        target_addr,
        selected_services,
        visualize=True,
        vis_path="rfcomm_fsm.png"
    )

    if args.fuzz:
        dlcis_to_fuzz = sorted({s["port"] for s in selected_services
                                if s.get("protocol") == "RFCOMM" and isinstance(s.get("port"), int)})
        if not dlcis_to_fuzz:
            print("[!] No RFCOMM DLCIs to fuzz.")
            return
        """
        # Run service exerciser pre-phase
        service_exerciser(
            target_addr=target_addr,
            services=selected_services,
            duration_sec=450,          # tweak if desired
            hb_interval_sec=0.4,     # 300–500 ms suggested
            max_services=None,       # or an int to cap
        )
        """

        # TIME-BASED (if --time N given), else COUNT-BASED
        if args.time and args.time > 0:
            fuzz_rfcomm(
                target_addr=target_addr,
                dlcis=dlcis_to_fuzz,
                time_limit_seconds=args.time,      # ← time-based
                time_retry=args.timeretry,         # ← optional retry behavior
                quiet=True,
                jitter_range=(0.0, 0.05),
                progress_every=1,
                seed=None,
            )
        else:
            fuzz_rfcomm(
                target_addr=target_addr,
                dlcis=dlcis_to_fuzz,
                per_dlci_mutations=200,            # ← count-based
                quiet=True,
                jitter_range=(0.0, 0.05),
                progress_every=1,
                seed=None,
            )
        return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(130)
