# rfcomm/modules/mutation.py
# Time-based RFCOMM fuzzer with optional retry and equal split across CTRL (dlci0) + data DLCIs.
# Also supports a simple count-based fallback for compatibility.

from layer.rfcomm.types.uih import UIH
from layer.rfcomm.types.disc import DISC
from layer.rfcomm.types.data import DATA
from layer.rfcomm.types.mx.msc import MSC
from layer.rfcomm.types.mx.rpn import RPN
from layer.rfcomm.types.mx.rls import RLS
from layer.rfcomm.types.mx.fcon import FCON
from layer.rfcomm.types.mx.fcoff import FCOFF
from layer.rfcomm.types.mx.test import TEST

import random
import time
from datetime import date, datetime

import bluetooth
from termcolor import colored

# Core state/constants provided by your repo
from lib.state import (
    CTRL_CHANNEL,
    RFCOMM_FRAMES,
    RFCOMM_COMMANDS,
)

from modules.logger import Logger
from modules.testsuite import (
    ensure_rfcomm_session,
    ensure_dlci_open,
    ensure_dlci_closed,
)

# -----------------
# Logging setup
# -----------------
now = datetime.now()
t = str(now)[11:19].replace(":", "", 2)
today = date.today().isoformat()
d = today[2:4] + today[5:7] + today[8:10]

def get_logtime():
    # Generate timestamp string (YYMMDDHHMMSS) for log folder
    return d + t

logger = Logger(get_logtime()) # create a logger instance for this fuzzing run

# -----------------
# Globals / knobs
# -----------------
pkt_cnt = 0
MUTATION_CNT = 200          # only used in count-mode
CHECK_BATCH = 25            # send this many packets per inner loop before checking/printing
SPAM_SLEEP = 0.001          # small sleep between sends if you want to throttle

# ---------------
# Helpers
# ---------------
def _progress_time(label: str, start_t: float, sent_total: int):
    """One-line time-mode progress: updates in place."""
    elapsed = int(time.time() - start_t)
    rate = (sent_total / elapsed) if elapsed > 0 else 0.0
    print(f"\r{label} t={elapsed}s pkts={sent_total} (~{rate:.1f}/s)", end="", flush=True)

def _progress_count(label: str, i: int, total: int):
    """One-line count-mode progress: updates in place."""
    print(f"\r{label} {i}/{total}", end="", flush=True)

def _finish_line():
    print("")

def _log_send(state_label: str, payload: bytes):
    global pkt_cnt
    pkt_cnt += 1
    logger.inputQueue({
        "no": pkt_cnt,
        "protocol": "RFCOMM",
        "sended_time": str(datetime.now()),
        "payload": payload,
        "crash": "n",
        "state": state_label,
    })

def _rand_frame():
    """Pick a random RFCOMM primitive to fuzz with (frame vs MX command)."""
    if random.random() < 0.5:
        return random.choice(RFCOMM_FRAMES)
    return random.choice(RFCOMM_COMMANDS)

def _build_random_pkt_for_dlci(dlci: int) -> bytes:
    cls = _rand_frame()
    if cls in RFCOMM_COMMANDS:
        # MX commands ride in UIH on CTRL and target the DLCI
        return UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, transition=False, fuzz=True, mx_type=cls)
    # Frames (SABM/UA/DM/DISC/UIH/DATA etc.); .gen signature differs by class, so try channel arg first
    try:
        return cls.gen(channel=dlci or CTRL_CHANNEL, fuzz=True)
    except TypeError:
        return cls.gen(fuzz=True)

def _spam_random_packets(sock, label: str, dlci: int, until_ts: float, start_t: float, sent_total: int):
    """
    Core inner loop: build and send up to CHECK_BATCH random packets on a given DLCI.
    - Stops if we hit end of time slice or socket errors.
    - Updates log and progress display.
    Returns: (packets_sent_this_batch, new_sent_total).
    """
    sent_in_batch = 0
    for _ in range(CHECK_BATCH):
        if time.time() >= until_ts:
            return sent_in_batch, sent_total
        pkt = _build_random_pkt_for_dlci(dlci)
        try:
            sock.send(pkt)
            _log_send(label, pkt)
            sent_in_batch += 1
            sent_total += 1
            # Update progress every 64 packets to keep console quiet
            if (sent_total & 63) == 0:
                _progress_time(label, start_t, sent_total)
        except bluetooth.BluetoothError:
            return 0, sent_total
        if SPAM_SLEEP:
            time.sleep(SPAM_SLEEP)
    return sent_in_batch, sent_total

def _gen_test_pkt_via_stack() -> bytes:
    """Legit RFCOMM UIH(TEST) frame via project types."""
    return UIH.gen(
        channel=CTRL_CHANNEL,
        channel_to_ctrl=CTRL_CHANNEL,
        transition=False,
        fuzz=False,
        mx_type=TEST
    )


# ===============================
# Time-based fuzzers
# ===============================

def fuzz_ctrl_open(target_addr, dlci_choices, duration_seconds=None, time_retry=False):
    """
    Time-based fuzzer for the control channel (DLCI=0).
    - First half of slice: exercise TEST frames (legit UIH(TEST)) repeatedly.
    - Second half: random UIH/MX frames targeted at each DLCI in round-robin.
    - If time_retry=True: will re-open session on errors until slice ends.
    """
    print(colored("[-] current state: CTRL_OPEN (DLCI=0)", "blue"))
    if duration_seconds is None or duration_seconds <= 0:
        return False
    # establish session
    sock = ensure_rfcomm_session(None, target_addr)
    if not sock:
        return False
    end = time.time() + int(duration_seconds)
    start = time.time()
    sent_total = 0
    dl_list = dlci_choices if dlci_choices else [1]
    idx = 0

    print("Fuzzing with TEST Packets\n")
    duration = max(0.0, end - start)           # seconds until end
    deadline = time.monotonic() + duration/2   # spend ~half of slice on TEST spam
    test_pkt = _gen_test_pkt_via_stack()
    i = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock.send(test_pkt)
        _log_send("[CTRL_OPEN:TEST]", test_pkt)
        i += 1
        if (i & 255) == 0:
            _progress_time("[CTRL_OPEN:TEST]", start, sent_total + i)
        if SPAM_SLEEP:
            time.sleep(min(SPAM_SLEEP, remaining))

    sent_total += i
    _finish_line()



    while time.time() < end:
        target_dlci = dl_list[idx % len(dl_list)]
        sent, sent_total = _spam_random_packets(sock, "[CTRL_OPEN]", target_dlci, end, start, sent_total)
        if sent > 0:
            idx += 1
            continue
        # error: either give up this slice (no retry) or retry open until time ends
        if not time_retry:
            break
        reopened = False
        while time.time() < end:
            # close & re-open RFComm session
            try:
                if sock:
                    sock.close()
            except Exception:
                pass
            try:
                sock = ensure_rfcomm_session(None, target_addr)
                if sock:
                    reopened = True
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not reopened:
            break
    _finish_line()
    try:
        if sock: sock.close()
    except Exception:
        pass
    return False

def fuzz_data_open(target_addr, dlci: int, duration_seconds=None, time_retry=False):
    """
    Time-based fuzzer for a single DATA DLCI.
    - Opens the DLCI once.
    - Sends random frames until slice ends.
    - Optionally retries if disconnect happens.
    """
    print(colored(f"[-] current state: DATA_OPEN (DLCI={dlci})", "blue"))
    if duration_seconds is None or duration_seconds <= 0:
        return False
    # open once
    open_set = set()
    sock = ensure_dlci_open(None, target_addr, dlci, open_set)
    if not sock:
        return False
    end = time.time() + int(duration_seconds)
    start = time.time()
    sent_total = 0
    while time.time() < end:
        sent, sent_total = _spam_random_packets(sock, f"[DATA_OPEN:{dlci}]", dlci, end, start, sent_total)
        if sent > 0:
            continue
        if not time_retry:
            break
        # retry loop
        reopened = False
        while time.time() < end:
            try:
                if sock:
                    sock.close()
            except Exception:
                pass
            try:
                sock = ensure_dlci_open(None, target_addr, dlci, open_set)
                if sock:
                    reopened = True
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not reopened:
            break
    _finish_line()
    try:
        sock = ensure_dlci_closed(sock, target_addr, dlci, open_set)
    except Exception:
        pass
    try:
        if sock: sock.close()
    except Exception:
        pass
    return False

# ===============================
# Public entry points
# ===============================

def fuzzing(target_addr, profile_name=None, port=None, sm_like=None, test_info=None, path=None):
    """
    If test_info has "time_limit_seconds", we run time-mode:
      - Equal split across CTRL + discovered DLCIs.
      - Optional "time_retry" bool to keep retrying within slice.
    Otherwise, this entry does nothing (main flow uses fuzz_rfcomm).
    """
    total_time = None
    time_retry = False
    if isinstance(test_info, dict):
        total_time = int(test_info.get("time_limit_seconds") or 0)
        time_retry = bool(test_info.get("time_retry", False))
    if not total_time:
        return

    # Discover DLCIs from state machine if provided, else default to [1]
    dlcis = [1]
    try:
        if sm_like is not None:
            # prefer DATA_OPEN states like "DATA_OPEN_17"
            states = list(getattr(sm_like, "states", []))
            out = []
            for s in states:
                if isinstance(s, str) and s.startswith("DATA_OPEN_"):
                    try:
                        out.append(int(s.split("_")[-1]))
                    except Exception:
                        pass
            if out:
                dlcis = out
    except Exception:
        pass

    # Equal split across CTRL + DLCIs
    targets_count = 1 + len(dlcis)
    per_slice = max(1, total_time // targets_count)

    fuzz_ctrl_open(target_addr, dlcis, duration_seconds=per_slice, time_retry=time_retry)
    for dl in dlcis:
        fuzz_data_open(target_addr, dl, duration_seconds=per_slice, time_retry=time_retry)

def fuzz_rfcomm(target_addr, dlcis, per_dlci_mutations=400, quiet=True, jitter_range=(0.0, 0.05),
                progress_every=25, seed=None, time_limit_seconds=None, time_retry=False):
    """
    Main entrypoint used by rfcomm/main.py
    Modes:
    - Time-based (if --time is set): split total_time across CTRL + each DLCI.
    - Count-based (default): send per_dlci_mutations random packets per DLCI.
    Handles seeding, logging, progress display.
    """
    if seed is not None:
        random.seed(seed)

    dlcis = dlcis or [1]

    if time_limit_seconds:
        targets_count = 1 + len(dlcis)  # CTRL + DLCIs
        per_slice = max(1, int(time_limit_seconds) // targets_count)

        # CTRL slice
        fuzz_ctrl_open(target_addr, dlcis, duration_seconds=per_slice, time_retry=time_retry)
        # Each DLCI slice
        for d in dlcis:
            fuzz_data_open(target_addr, int(d), duration_seconds=per_slice, time_retry=time_retry)
        # Finalize logs once per run
        logger.logUpdate()
        print(f"[+] Tested {pkt_cnt} packets")
        return

    # -------- Count-mode fallback (random, deterministic count) --------
    for d in dlcis:
        print(colored(f"[-] current state: DATA_OPEN (DLCI={d})", "blue"))
        open_set = set()
        sock = ensure_dlci_open(None, target_addr, int(d), open_set)
        if not sock:
            continue
        for i in range(1, int(per_dlci_mutations) + 1):
            pkt = _build_random_pkt_for_dlci(int(d))
            try:
                sock.send(pkt)
                _log_send(f"[DATA_OPEN:{d}]", pkt)
            except bluetooth.BluetoothError:
                break
            if (i & 31) == 0:
                _progress_count(f"[DATA_OPEN:{d}]", i, int(per_dlci_mutations))
        _finish_line()
        try:
            sock = ensure_dlci_closed(sock, target_addr, int(d), open_set)
        except Exception:
            pass
        try:
            if sock: sock.close()
        except Exception:
            pass

    logger.logUpdate()
    print(f"[+] Tested {pkt_cnt} packets")
