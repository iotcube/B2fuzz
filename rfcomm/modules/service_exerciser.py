# rfcomm/modules/service_exerciser.py
# Pre-phase "service exerciser": iterate discovered services (RFCOMM/L2CAP),
# open a userspace socket, send benign seeds, then high‑rate short payloads.
# Output: one updating line per service, e.g. "[DATA_OPEN:16] t=65s pkts=3136 (~48.2/s)".

import time, random, string, bluetooth

# Tunables (inline; no new CLI)
DEFAULT_DURATION_SEC     = 3       # total time per service
DEFAULT_HB_INTERVAL_SEC  = 0.01    # heartbeat cadence (lower -> more packets)
DEFAULT_MAX_SERVICES     = None    # limit number of services to exercise

# -------- generic random text generator (no vehicle references) --------
def _rand_id(n=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(n))

def _rand_cmd():
    # short cmd-like token + CR
    length = random.randint(1, 6)
    return ("AT" + _rand_id(length) + "\r").encode("utf-8")  # harmless ASCII + CR

def _rand_number():
    # short numeric string
    if random.randint(0, 1) == 0:
        return ("0" + str(random.randint(0, 999))).encode("utf-8")
    return str(random.randint(0, 99999)).encode("utf-8")

def _rand_printable():
    # small printable blob (may contain whitespace)
    length = random.randint(1, 20)
    s = ''.join(random.choice(string.printable) for _ in range(length))
    return s.encode("utf-8", errors="ignore")

def _random_payload():
    # 40% cmd-like (ends with CR), 40% numeric, 20% printable
    pick = _rand_id(1, "12312")
    if pick == "1":
        return _rand_cmd()
    elif pick == "2":
        return _rand_number()
    else:
        return _rand_printable()

# -------- helpers --------
def _mk_sock(proto: str):
    if proto == "RFCOMM": return bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    if proto == "L2CAP":  return bluetooth.BluetoothSocket(bluetooth.L2CAP)
    return None

def _progress_line(label: str, start_t: float, count: int):
    elapsed = int(time.time() - start_t)
    rate = (count / elapsed) if elapsed > 0 else 0.0
    print(f"\r{label} t={elapsed}s pkts={count} (~{rate:.1f}/s)", end="", flush=True)

def _finish_line():
    print("")

# -------- main entry --------
def service_exerciser(target_addr: str,
                      services: list,
                      duration_sec: int = DEFAULT_DURATION_SEC,
                      hb_interval_sec: float = DEFAULT_HB_INTERVAL_SEC,
                      max_services: int | None = DEFAULT_MAX_SERVICES):
    """
    Iterate services in the given order, connect & send:
      - two simple ASCII seeds,
      - then randomized short payloads at the configured cadence.
    Prints exactly one line per service with running totals.
    """
    printed_header = False
    exercised = 0

    for svc in services:
        if max_services is not None and exercised >= max_services:
            break

        proto = (svc.get("protocol") or "").upper()
        port  = svc.get("port")
        if proto not in ("RFCOMM", "L2CAP") or not isinstance(port, int):
            continue

        if not printed_header:
            print("\n[Pre‑phase] Service Exerciser")
            print("--------------------------------")
            printed_header = True

        label = f"[DATA_OPEN:{port}]" if proto == "RFCOMM" else f"[L2CAP:{port}]"
        sock = _mk_sock(proto)
        if not sock:
            print(f"{label} t=0s pkts=0 (~0.0/s)")
            print("")
            continue

        exercised += 1
        sent = 0
        start_t = time.time()

        try:
            # connect
            sock.connect((target_addr, port))

            # two benign ASCII seeds (wake-up probes)
            for seed in (b"HELLO\r", b"PING\r"):
                try:
                    sock.send(seed); sent += 1
                except Exception:
                    break

            # heartbeat / random payloads
            end_ts = time.time() + max(1, int(duration_sec))
            first_tick = True
            while time.time() < end_ts:
                try:
                    payload = _random_payload()
                    sock.send(payload); sent += 1
                    # update line at start and then every 64 sends
                    if first_tick or (sent & 63) == 0:
                        _progress_line(label, start_t, sent)
                        first_tick = False
                    if hb_interval_sec:
                        time.sleep(hb_interval_sec)
                except bluetooth.BluetoothError:
                    _progress_line(label, start_t, sent)
                    break

            # finalize line
            _progress_line(label, start_t, sent)
            _finish_line()
            print("")  # spacing between profiles

        except Exception:
            # connection failed: print a single result line
            _progress_line(label, start_t, sent)
            _finish_line()
            print("")

        finally:
            try: sock.close()
            except Exception: pass
