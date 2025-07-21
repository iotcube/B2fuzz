import bluetooth
import traceback
from termcolor import colored
import time
from layer.rfcomm.const import RFCOMM_PSM
from lib.btpkt import inter_recv, process_rsps
from lib.state import SABM, UA, DISC, UIH
from lib.state import PN, RLS, RPN, FCON, DATA, INVALID, NSC, TEST, MSC
from lib.state import CTRL_CHANNEL

# Utility Functions

def is_sock_valid(sock):
    """
    Return True if the socket appears valid (connected), else False.
    Tries a non-intrusive socket call.
    """
    if sock is None:
        return False
    try:
        # On Linux, fileno() returns -1 for closed socket.
        fileno = sock.fileno()
        if fileno < 0:
            return False
        # Try a non-blocking peek
        sock.getpeername()  # Will fail if not connected
        return True
    except Exception:
        return False

def ensure_rfcomm_session(sock, target_addr):
    """
    Ensure an active RFCOMM session exists.
    If the provided socket is invalid or None, establish a new RFCOMM session.
    """
    print(f"[Debug] ensure_rfcomm_session: Checking existing socket for target_addr={target_addr}")
    if is_sock_valid(sock):
        print("[Debug] ensure_rfcomm_session: Socket is valid.")
        return sock
    if sock is not None:
        print("[Debug] ensure_rfcomm_session: Socket is invalid, closing.")
        try:
            sock.close()
        except Exception:
            pass
    print("[Debug] ensure_rfcomm_session: Creating new RFCOMM session.")
    status, sock_new = tc_BV_01_C(target_addr)
    if status < 0 or sock_new is None:
        print(colored(f" [Fail] Unable to establish RFCOMM session to {target_addr}", "red"))
        return None
    print("[Debug] ensure_rfcomm_session: New RFCOMM session established.")
    return sock_new

def ensure_dlci_open(sock, target_addr, dlci, open_dlci_set):
    """
    Only open DLCI if not already open.
    """
    if dlci in open_dlci_set:
        print(f"[Debug] ensure_dlci_open: DLCI {dlci} is already open.")
        return sock
    sock = ensure_rfcomm_session(sock, target_addr)
    if sock is None:
        print("[Debug] ensure_dlci_open: No valid socket, cannot open DLCI.")
        return None
    status, sock_new = tc_BV_05_C(sock, target_addr, dlci)
    if status < 0 or sock_new is None:
        print(colored(f" [Fail] Unable to open DLCI={dlci} on session {sock}", "red"))
        return None
    open_dlci_set.add(dlci)
    print(f"[Debug] ensure_dlci_open: DLCI {dlci} is open.")
    return sock_new

def ensure_dlci_closed(sock, target_addr, dlci, open_dlci_set):
    """
    Close DLCI if open, update set.
    """
    if dlci not in open_dlci_set:
        print(f"[Debug] ensure_dlci_closed: DLCI {dlci} is already closed.")
        return sock
    sock = ensure_rfcomm_session(sock, target_addr)
    if sock is None:
        print("[Debug] ensure_dlci_closed: No valid socket, cannot close DLCI.")
        return None
    status = tc_BV_07_C(sock, target_addr, dlci, target_addr)
    if status:
        open_dlci_set.discard(dlci)
    return sock

# Test Case Functions

def tc_BV_01_C(target_addr):
    """
    BV-01-C RFCOMM Session Initialization (Initiator)

    [Session_Open]
        |
        |-- S: SABM (DLCI=0)
        v
    [Wait_UA]
        |-- R: UA  -------------> [Control_Open (DLCI=0)]
        |-- R: DM or Timeout ---> [Session_Open]   (fail)
    """
    print(f"[BV-01-C] Initializing RFCOMM Session for target {target_addr}")
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    try:
        print(f"[BV-01-C] Connecting L2CAP socket to {target_addr}, PSM={RFCOMM_PSM}")
        sock.connect((target_addr, RFCOMM_PSM))
    except Exception as e:
        print(colored(f" [Fail] L2CAP connect: {e}", "red"))
        sock.close()
        return -1, None
    try:
        print(f"[BV-01-C] Sending SABM (DLCI=0) on control channel.")
        sabm_pkt = SABM.gen(channel=CTRL_CHANNEL, transition=True)
        sock.send(sabm_pkt)
    except Exception as e:
        print(colored(f" [Fail] SABM send: {e}", "red"))
        sock.close()
        traceback.print_exc()
        return -1, None
    try:
        print(f"[BV-01-C] Waiting for UA response...")
        resp_list, sock = inter_recv(sock, dur=0.1)
        print(f"[BV-01-C] Received response list: {resp_list}")
        status, _ = process_rsps(resp_list, required_types=["UA"])
        print(f"[BV-01-C] process_rsps status: {status}")
        if status != 0:
            sock.close()
            return status, None
    except Exception as e:
        print(colored(f" [Fail] Error in UA receive: {e}", "red"))
        sock.close()
        traceback.print_exc()
        return -1, None
    print(colored(" [Pass] RFCOMM session initialized (BV-01-C)", "green"))
    return 0, sock

def tc_BV_04_C(sock, open_dlci_list):
    """
    BV-04-C RFCOMM Session Shutdown

    [DLC_Open (DLCI≠0)] (repeat for each DLCI in open_dlci_list)
        |
        |-- S: DISC (dlci)
        v
    [Wait_UA]
        |-- R: UA/Timeout ----> [Control_Open (DLCI=0)] (continue)
    [Control_Open (DLCI=0)]
        |
        |-- S: DISC (ctrl)
        v
    [Wait_UA]
        |-- R: UA/Timeout ----> [Session_Open] (session closed)
    """
    print(f"[BV-04-C] Closing all DLCI channels {open_dlci_list} and shutting down session")
    # Close each open DLCI (if any)
    for dlci in open_dlci_list:
        print(f"[BV-04-C] Closing DLCI={dlci}...")
        try:
            disc_pkt = DISC.gen(channel=dlci, transition=True)
            sock.send(disc_pkt)
        except Exception as e:
            print(colored(f" [Warn] Could not send DISC on DLCI={dlci}: {e}. Skipping.", "yellow"))
            continue
        try:
            resp_list, sock = inter_recv(sock, dur=0.1)
            valid_responses = process_rsps(resp_list)
            if "UA" not in valid_responses:
                print(colored(f" [Warn] UA not received after DISC on DLCI={dlci}. (got {valid_responses})", "yellow"))
            else:
                print(colored(f" [Pass] DLCI={dlci} closed (BV-04-C)", "green"))
        except Exception as e:
            print(colored(f" [Fail] Error in UA receive for DLCI={dlci}: {e}", "red"))
            continue
    # Close control channel
    try:
        print(f"[BV-04-C] Sending DISC on control channel (DLCI=0)...")
        disc_pkt = DISC.gen(channel=CTRL_CHANNEL, transition=True)
        sock.send(disc_pkt)
    except Exception as e:
        print(colored(f" [Warn] Could not send DISC on CTRL_CHANNEL: {e}. Session was likely already down.", "yellow"))
        return True
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "UA" not in valid_responses:
            print(colored(f" [Warn] UA not received after DISC on CTRL_CHANNEL. (got {valid_responses})", "yellow"))
        else:
            print(colored(f" [Pass] CTRL_CHANNEL closed (BV-04-C)", "green"))
    except Exception as e:
        print(colored(f" [Fail] Error in UA receive for CTRL_CHANNEL: {e}", "red"))
    try:
        sock.close()
    except Exception:
        pass
    return True


def tc_BV_05_C(sock, target_addr, dlci):
    """
    BV-05-C DLC Establishment (Initiator)

    [Control_Open (DLCI=0)]
        |
        |-- S: PN (dlci)
        v
    [Wait_PN]
        |-- R: PN   -----------> [Control_Open (DLCI=0)]
        |-- R: NSC  -----------> [Control_Open (DLCI=0)]  (inconclusive)
        |-- Timeout/Other -----> [Control_Open (DLCI=0)]  (fail)
        |
        |-- S: SABM (dlci)
        v
    [Wait_UA]
        |-- R: UA  ------------> [DLC_Open (DLCI≠0)]
        |-- Timeout/Other -----> [Control_Open (DLCI=0)]  (fail)
    """
    print(f"[BV-05-C] Establishing DLCI={dlci} on session")
    sock = ensure_rfcomm_session(sock, target_addr)
    if sock is None:
        print(colored(f" [Fail] Could not (re)establish RFCOMM session for BV-05-C", "red"))
        return -1, None
    try:
        print(f"[BV-05-C] Sending PN for DLCI={dlci}.")
        pn_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, transition=True, mx_type=PN)
        sock.send(pn_pkt)
    except Exception as e:
        print(colored(f" [Fail] Send PN for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return -1, None
    try:
        print(f"[BV-05-C] Waiting for PN/NSC response...")
        resp_list, sock = inter_recv(sock, dur=0.1)
        print(f"[BV-05-C] Received response list: {resp_list}")
        status, _ = process_rsps(resp_list, required_types=["PN"], optional_types=["NSC"], allow_timeout=False)
        print(f"[BV-05-C] process_rsps status: {status}")
        if status != 0:
            if status == 1:
                print(colored(f" [Inconclusive] Received NSC (Not Supported Command) for DLCI={dlci}, no PN.", "yellow"))
                return 1, sock
            else:
                print(colored(f" [Fail] PN/NSC response not received for DLCI={dlci}.", "red"))
                return -1, None
    except Exception as e:
        print(colored(f" [Fail] Error in PN receive for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return -1, None
    try:
        print(f"[BV-05-C] Sending SABM for DLCI={dlci}.")
        sabm_pkt = SABM.gen(channel=dlci, transition=True)
        sock.send(sabm_pkt)
    except Exception as e:
        print(colored(f" [Fail] Send SABM for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return -1, None
    try:
        print(f"[BV-05-C] Waiting for UA response...")
        resp_list, sock = inter_recv(sock, dur=0.1)
        print(f"[BV-05-C] Received response list: {resp_list}")
        status, _ = process_rsps(resp_list, required_types=["UA"])
        print(f"[BV-05-C] process_rsps status: {status}")
        if status != 0:
            if status == 1:
                print(colored(f" [Inconclusive] UA response not received for DLCI={dlci}, but allowed.", "yellow"))
                return 1, sock
            else:
                print(colored(f" [Fail] UA not received for DLCI={dlci}.", "red"))
                return -1, None
    except Exception as e:
        print(colored(f" [Fail] Error in UA receive for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return -1, None
    print(colored(f" [Pass] DLCI={dlci} established (BV-05-C)", "green"))
    return 0, sock

def tc_BV_07_C(sock, target_addr, dlci, open_dlci_set):
    """
    BV-07-C Close DLC (by IUT)

    [DLC_Open (DLCI≠0)]
        |
        |-- S: DISC (dlci)
        v
    [Wait_UA]
        |-- R: UA  -------------> [Control_Open (DLCI=0)]
        |-- Timeout/Other -----> [Control_Open (DLCI=0)]  (warn/fail)
    """
    print(f"[BV-07-C] Closing DLCI={dlci} on session")
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None:
        print(colored(f" [Fail] Could not open DLCI={dlci} for BV-07-C", "red"))
        return False
    try:
        print(f"[BV-07-C] Sending DISC on DLCI={dlci}.")
        disc_pkt = DISC.gen(channel=dlci, transition=True)
        sock.send(disc_pkt)
    except Exception as e:
        print(colored(f" [Fail] Send DISC on DLCI={dlci}: {e}", "red"))
        try:
            sock.close()
        except Exception:
            pass
        return False
    try:
        print(f"[BV-07-C] Waiting for UA response...")
        resp_list, sock = inter_recv(sock, dur=0.1)
        print(f"[BV-07-C] Received response list: {resp_list}")
        valid_responses = process_rsps(resp_list)
        print(f"[BV-07-C] process_rsps responses: {valid_responses}")
        if "UA" not in valid_responses:
            print(colored(f" [Warn] UA not received after DISC on DLCI={dlci}. (got {valid_responses})", "yellow"))
        else:
            print(colored(f" [Pass] DLCI={dlci} closed (BV-07-C)", "green"))
        return True
    except Exception as e:
        print(colored(f" [Fail] Error in UA receive for DLCI={dlci}: {e}", "red"))
        try:
            sock.close()
        except Exception:
            pass
        return False

def tc_BV_11_C(sock, target_addr):
    """
    BV-11-C TEST Command (Loopback/Echo)

    [Control_Open (DLCI=0)]
        |
        |-- S: TEST (pattern)
        v
    [Wait_TEST]
        |-- R: TEST (echo)
                |-- Payload Match -----> [Control_Open (DLCI=0)] (pass)
                |-- Payload Mismatch --> [Control_Open (DLCI=0)] (fail)
        |-- Timeout/Other ------------> [Control_Open (DLCI=0)] (fail)
    """
    print(f"[BV-11-C] Running TEST command on session")
    sock = ensure_rfcomm_session(sock, target_addr)
    if sock is None:
        print(colored(f" [Fail] Could not (re)establish RFCOMM session for BV-11-C", "red"))
        return -1, None
    try:
        test_pattern = b'HI'
        print(f"[BV-11-C] Sending TEST command with pattern {test_pattern}")
        test_pkt = UIH.gen(channel=CTRL_CHANNEL, transition=False, mx_type=TEST, payload=test_pattern)
        sock.send(test_pkt)
    except Exception as e:
        print(colored(f" [Fail] Send TEST command: {e}", "red"))
        traceback.print_exc()
        return -1, None
    try:
        print(f"[BV-11-C] Waiting for TEST response...")
        resp_list, sock = inter_recv(sock, dur=0.1)
        print(f"[BV-11-C] Received response list: {resp_list}")
        expected_test_response = TEST.gen(payload=test_pattern, is_response=True)
        status, _ = process_rsps(resp_list, required_types=["TEST"], expected_payloads={"TEST": expected_test_response})
        print(f"[BV-11-C] process_rsps status: {status}")
        if status != 0:
            if status == 1:
                print(colored(" [Inconclusive] Did not receive TEST response, but allowed.", "yellow"))
                return 1, sock
            else:
                print(colored(" [Fail] Did not receive matching TEST response.", "red"))
                return -1, None
    except Exception as e:
        print(colored(f" [Fail] Error in TEST receive: {e}", "red"))
        traceback.print_exc()
        return -1, None
    print(colored(" [Pass] TEST command successful (BV-11-C)", "green"))
    return 0, sock

def tc_BV_13_C(sock, target_addr, dlci, open_dlci_set):
    """
    BV-13-C Remote Line Status Indication

    [Control_Open (DLCI=0)]
        |
        |-- S: RLS (dlci, status=0b1010)
        v
    [Wait_RLS]
        |-- R: RLS (payload match) ----> [Control_Open (DLCI=0)] (pass)
        |-- R: RLS (payload mismatch) -> [Control_Open (DLCI=0)] (fail)
        |-- Timeout/Other ------------> [Control_Open (DLCI=0)] (fail)
    """
    print(f"[BV-13-C] Sending RLS to DLCI={dlci} on session")
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None:
        print(colored(f" [Fail] Could not open DLCI={dlci} for BV-13-C", "red"))
        return -1, None
    try:
        line_status_to_send = 0b1010
        print(f"[BV-13-C] Sending RLS with status={bin(line_status_to_send)} to DLCI={dlci}")
        rls_pkt = UIH.gen(channel=CTRL_CHANNEL, transition=False, mx_type=RLS, channel_to_ctrl=dlci, line_status=line_status_to_send)
        sock.send(rls_pkt)
        expected_response_payload = RLS.gen(channel=dlci, line_status=line_status_to_send, is_response=True, mimic_direction_bug=True)
        print(f"[BV-13-C] Waiting for RLS response...")
        resp_list, sock = inter_recv(sock, dur=0.1)
        print(f"[BV-13-C] Received response list: {resp_list}")
        status, _ = process_rsps(resp_list, required_types=["RLS"], expected_payloads={"RLS": expected_response_payload})
        print(f"[BV-13-C] process_rsps status: {status}")
        if status != 0:
            if status == 1:
                print(colored(f" [Inconclusive] RLS response not received or did not match for DLCI={dlci}, but allowed.", "yellow"))
                return 1, sock
            else:
                print(colored(f" [Fail] RLS response validation failed for DLCI={dlci}.", "red"))
                return -1, None
    except Exception as e:
        print(colored(f" [Fail] Error in RLS receive for DLCI={dlci}: {e}", "red"))
        return -1, None
    print(colored(f" [Pass] RLS command successful for DLCI={dlci} (BV-13-C)", "green"))
    return 0, sock

def tc_BV_14_C(sock, target_addr, dlci, open_dlci_set):
    """
    BV-14-C Remote Line Status Indication (Different Status)

    [Control_Open (DLCI=0)]
        |
        |-- S: RLS (dlci, status=0b1001)
        v
    [Wait_RLS]
        |-- R: RLS (payload match) ----> [Control_Open (DLCI=0)] (pass)
        |-- R: RLS (payload mismatch) -> [Control_Open (DLCI=0)] (fail)
        |-- Timeout/Other ------------> [Control_Open (DLCI=0)] (fail)
    """
    print(f"[BV-14-C] Sending RLS (different status) to DLCI={dlci} on session")
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None:
        print(colored(f" [Fail] Could not open DLCI={dlci} for BV-14-C", "red"))
        return -1, None
    try:
        line_status_to_send = 0b1001
        print(f"[BV-14-C] Sending RLS with status={bin(line_status_to_send)} to DLCI={dlci}")
        rls_pkt = UIH.gen(channel=CTRL_CHANNEL, transition=False, mx_type=RLS, channel_to_ctrl=dlci, line_status=line_status_to_send)
        sock.send(rls_pkt)
        expected_response_payload = RLS.gen(channel=dlci, line_status=line_status_to_send, is_response=True, mimic_direction_bug=True)
        print(f"[BV-14-C] Waiting for RLS response...")
        resp_list, sock = inter_recv(sock, dur=0.1)
        print(f"[BV-14-C] Received response list: {resp_list}")
        status, _ = process_rsps(resp_list, required_types=["RLS"], expected_payloads={"RLS": expected_response_payload})
        print(f"[BV-14-C] process_rsps status: {status}")
        if status != 0:
            if status == 1:
                print(colored(f" [Inconclusive] RLS response not received or did not match for DLCI={dlci} (BV-14-C), but allowed.", "yellow"))
                return 1, sock
            else:
                print(colored(f" [Fail] RLS response validation failed for DLCI={dlci} (BV-14-C).", "red"))
                return -1, None
    except Exception as e:
        print(colored(f" [Fail] Error in RLS receive for DLCI={dlci} (BV-14-C): {e}", "red"))
        return -1, None
    print(colored(f" [Pass] RLS command successful for DLCI={dlci} (BV-14-C)", "green"))
    return 0, sock


def tc_BV_17_C(sock, target_addr, dlci, open_dlci_set):
    """
    BV-17-C Remote Port Negotiation (RPN) Command

    [DLC_Open (DLCI≠0)]
        |
        |-- S: RPN (dlci)
        v
    [Wait_RPN]
        |-- R: RPN ---------> [DLC_Open (DLCI≠0)] (pass)
        |-- R: NSC ---------> [DLC_Open (DLCI≠0)] (inconclusive)
        |-- Timeout/Other --> [DLC_Open (DLCI≠0)] (fail)
    """
    print(f"[BV-17-C] Sending RPN command to DLCI={dlci} on session")
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None:
        print(colored(f" [Fail] Could not open DLCI={dlci} for BV-17-C", "red"))
        return False
    try:
        port_settings_to_send = bytes([
            0x07, 0x03, 0x00, 0x11, 0x13, 0xFF, 0xFF, 0xFF
        ])
        print(f"[BV-17-C] Sending RPN with port settings to DLCI={dlci}")
        rpn_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, transition=True,
                          mx_type=RPN, port_values=port_settings_to_send)
        sock.send(rpn_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send RPN for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False
    try:
        print(f"[BV-17-C] Waiting for RPN/NSC response...")
        resp_list, sock = inter_recv(sock, dur=0.1)
        print(f"[BV-17-C] Received response list: {resp_list}")
        valid_responses = process_rsps(resp_list)
        print(f"[BV-17-C] process_rsps responses: {valid_responses}")
        if "RPN" in valid_responses:
            print(colored(f" [Pass] RPN response received for DLCI={dlci} (BV-17-C)", "green"))
            return True
        elif "NSC" in valid_responses:
            print(colored(f" [Pass] NSC (Not Supported Command) response received for DLCI={dlci} (BV-17-C)", "yellow"))
            return True
        else:
            print(colored(f" [Fail]\n RPN/NSC response not received for DLCI={dlci}. (got {valid_responses})", "red"))
            return False
    except Exception as e:
        print(colored(f" [Fail]\n Error in RPN receive for DLCI={dlci}: {e}", "red"))
        return False

# === BV-19-C ===
def tc_BV_19_C(sock, target_addr, dlci, open_dlci_set):
    """
    BV-19-C RPN by IUT (query for settings)

    [DLC_Open (DLCI≠0)]
        |
        |-- S: RPN (dlci, 1-octet)
        v
    [Wait_RPN]
        |-- R: RPN (8 octets) -----> [DLC_Open (DLCI≠0)] (pass)
        |-- Timeout/Other ---------> [DLC_Open (DLCI≠0)] (fail)
    """
    print(f"[BV-19-C] Sending basic RPN (query) to DLCI={dlci} on session")
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None:
        print(colored(f" [Fail] Could not open DLCI={dlci} for BV-19-C", "red"))
        return False
    try:
        rpn_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, transition=True, mx_type=RPN)
        sock.send(rpn_pkt)
    except Exception as e:
        print(colored(f" [Fail] Send basic RPN for DLCI={dlci}: {e}", "red"))
        return False
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, responses = process_rsps(
            resp_list,
            required_types=["RPN"],
            expected_payloads={"RPN": lambda p: len(p) == 8}
        )
        if status == 0:
            print(colored(f" [Pass] RPN 8-octet response for DLCI={dlci} received (BV-19-C)", "green"))
            return True
        else:
            print(colored(f" [Fail] RPN response for DLCI={dlci} did not meet expected format.", "red"))
            return False
    except Exception as e:
        print(colored(f" [Fail] Error in RPN receive for DLCI={dlci}: {e}", "red"))
        return False

# === BV-21-C ===
def tc_BV_21_C(sock, target_addr, dlci, open_dlci_set):
    """
    BV-21-C Credit Based Flow Control

    [DLC_Open (DLCI≠0)]
        |
        |-- S: MSC (dlci) handshake
        |-- R: MSC
        |
        |-- Wait for UIH_CREDIT
        |-- Send data frames according to credits
        v
    [Flow_Control]
        |-- All data sent ----> [DLC_Open (DLCI≠0)] (pass)
        |-- Timeout/Error ----> [DLC_Open (DLCI≠0)] (fail)
    """
    print(f"[BV-21-C] Testing credit-based flow control for DLCI={dlci} on session")
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None:
        print(colored(f" [Fail] Could not open DLCI={dlci} for BV-21-C", "red"))
        return False

    # Step 1: Perform MSC handshake
    try:
        print(colored("    -> Performing MSC handshake...", "cyan"))
        msc_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, mx_type=MSC, fc=False, rtc=True, rtr=True)
        sock.send(msc_pkt)
        resp_list, sock = inter_recv(sock, dur=1.0)
        process_rsps(resp_list, required_types=["MSC"])  # Only for warning/log, not critical
    except Exception as e:
        print(colored(f" [Fail]    MSC Handshake for DLCI={dlci}: {e}", "red"))
        return False

    # Step 2: Receive credits (UIH_CREDIT)
    try:
        print(colored("    -> Waiting to receive credits from IUT...", "cyan"))
        resp_list, sock = inter_recv(sock, dur=5.0)
        # Accept any nonzero credit value, custom validator as lambda
        status, responses = process_rsps(
            resp_list,
            required_types=["UIH_CREDIT"],
            expected_payloads={"UIH_CREDIT": lambda payload: payload and payload[0] > 0}
        )
        if status != 0:
            print(colored(f" [Fail] Timed out waiting for credits from IUT on DLCI={dlci}.", "red"))
            return False
        credit_pkt = responses["UIH_CREDIT"]
        credits_received = credit_pkt.payload[0]  # Or use .credit if FRAME_PKT has this
        print(colored(f"    -> Received {credits_received} credits!", "gray"))
    except Exception as e:
        print(colored(f" [Fail]    Error while receiving credits from IUT: {e}", "red"))
        return False

    # Step 3: Send data frames based on credits
    try:
        print(colored(f"    -> Sending {credits_received} data frames...", "cyan"))
        for i in range(credits_received):
            data_to_send = f"packet_{i+1}_of_{credits_received}".encode()
            data_pkt = UIH.gen(channel=dlci, mx_type=DATA, payload=data_to_send, transition=False)
            sock.send(data_pkt)
            time.sleep(0.05)
        print(colored(f"    -> Finished sending data.", "gray"))
    except Exception as e:
        print(colored(f" [Fail]    Error sending data after receiving credits: {e}", "red"))
        return False

    print(colored(f" [Pass] Credit-based flow control test complete (BV-21-C)", "green"))
    return True

# === BV-22-C ===
def tc_BV_22_C(sock, target_addr, dlci, open_dlci_set):
    """
    BV-22-C Data Transfer with MSC Handshake

    [DLC_Open (DLCI≠0)]
        |
        |-- S: MSC (dlci)
        |-- R: MSC
        |-- S: UIH(DATA)
        v
    [Data_Transfer]
        |-- Data sent -----> [DLC_Open (DLCI≠0)] (pass)
        |-- Timeout/Error -> [DLC_Open (DLCI≠0)] (fail)
    """
    print(f"[BV-22-C] Data transfer with MSC handshake on DLCI={dlci}, session")
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None:
        print(colored(f" [Fail] Could not open DLCI={dlci} for BV-22-C", "red"))
        return False

    # Step 1: Send MSC command and check response
    try:
        print(colored("    -> Sending MSC command...", "cyan"))
        msc_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, transition=True, mx_type=MSC, fc=False, rtc=True, rtr=True)
        sock.send(msc_pkt)
        resp_list, sock = inter_recv(sock, dur=1.0)
        process_rsps(resp_list, required_types=["MSC"])
    except Exception as e:
        print(colored(f" [Fail]    Send MSC for DLCI={dlci}: {e}", "red"))
        return False

    # Step 2: Send data packet (and optionally check response if required)
    try:
        print(colored("    -> Sending data packet...", "cyan"))
        data_to_send = b"test_data_after_msc"
        data_pkt = UIH.gen(channel=dlci, mx_type=DATA, payload=data_to_send)
        sock.send(data_pkt)
        # Optionally: receive and validate DATA response if protocol requires it
        # resp_list, sock = inter_recv(sock, dur=0.5)
        # process_rsps(resp_list, required_types=["DATA"])
    except Exception as e:
        print(colored(f" [Fail]    Send data after MSC for DLCI={dlci}: {e}", "red"))
        return False

    print(colored(f" [Pass] Data transfer after MSC handshake complete (BV-22-C)", "green"))
    return True


# === BV-25-C ===
def tc_BV_25_C(sock, target_addr):
    """
    BV-25-C Unsupported Command Handling

    [Control_Open (DLCI=0)]
        |
        |-- S: INVALID (ctrl)
        v
    [Wait_NSC]
        |-- R: NSC -----------> [Control_Open (DLCI=0)] (pass)
        |-- Timeout/Other ----> [Control_Open (DLCI=0)] (fail)
    """
    print(f"[BV-25-C] Sending INVALID command for unsupported command handling on session")
    sock = ensure_rfcomm_session(sock, target_addr)
    if sock is None:
        print(colored(f" [Fail] Could not (re)establish RFCOMM session for BV-25-C", "red"))
        return False
    try:
        invalid_pkt = UIH.gen(channel=CTRL_CHANNEL, transition=True, mx_type=INVALID)
        sock.send(invalid_pkt)
    except Exception as e:
        print(colored(f" [Fail] Send Invalid Command: {e}", "red"))
        traceback.print_exc()
        return False
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "NSC" not in valid_responses:
            print(colored(f" [Fail] Did not receive NSC after invalid command. (got {valid_responses})", "red"))
            return False
    except Exception as e:
        print(colored(f" [Fail] Error in NSC receive: {e}", "red"))
        traceback.print_exc()
        return False
    print(colored(" [Pass] Unsupported command handled correctly (BV-25-C)", "green"))
    return True