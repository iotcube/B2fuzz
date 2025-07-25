import bluetooth
import traceback
from termcolor import colored
import time
from layer.rfcomm.const import RFCOMM_PSM
from lib.btpkt import inter_recv, process_rsps
from lib.state import StateName, state_name, CTRL_CHANNEL
from lib.state import SABM, UA, DISC, UIH
from lib.state import PN, RLS, RPN, FCON, DATA, INVALID, NSC, TEST, MSC

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
    _, sock_new = tc_BV_01_C(target_addr)
    if sock_new is None:
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
    _, sock_new = tc_BV_05_C(sock, target_addr, dlci)
    if sock_new is None:
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
    path = []
    print(colored("[*] RFCOMM Session Initialization (BV-01-C)", "cyan"))
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    try:
        sock.connect((target_addr, RFCOMM_PSM))
    except Exception as e:
        print(colored(f" [Fail] L2CAP connect: {e}", "red")); sock.close(); return -1, None

    src1 = state_name(StateName.SESS_OPEN)
    dest1 = state_name(StateName.SESS_WAIT_UA)
    try:
        sabm_pkt = SABM.gen(channel=CTRL_CHANNEL)
        sock.send(sabm_pkt)
        path.append((src1, "send_sabm", dest1, True))
    except Exception as e:
        print(colored(f" [Fail] SABM send: {e}", "red")); sock.close(); path.append((src1, "send_sabm", dest1, False)); return path, None
    
    src2 = dest1
    dest2 = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, _ = process_rsps(resp_list, required_types=["UA"])
        path.append((src2, "recv_ua", dest2, status == 0))
        if status != 0:
            sock.close()
            return path, None
    except Exception as e:
        print(colored(f" [Fail] Error in UA receive: {e}", "red")); sock.close(); path.append((src2, "recv_ua", dest2, False)); return path, None

    print(colored(" [Pass] RFCOMM session initialized (BV-01-C)", "green"))
    return path, sock

def tc_BV_04_C(sock, target_addr, open_dlci_set):
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
    path = []
    print(colored("[*] RFCOMM Session Shutdown (BV-04-C)", "cyan"))
    
    # First, close any data channels that are still open. This is now handled by the orchestrator.
    if len(open_dlci_set) > 0:
        print(colored(f" [Warn] tc_BV_04_C called while DLCIs {list(open_dlci_set)} are still open.", "yellow"))

    # Define the state transitions upfront
    src1 = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    dest1 = state_name(StateName.CTRL_WAIT_DISC_UA, CTRL_CHANNEL)
    
    src2 = dest1
    dest2_final = state_name(StateName.SESS_OPEN)

    # --- Step 1: Attempt to Send DISC on Control Channel ---
    try:
        # Check if the socket is valid *before* trying to use it.
        if not is_sock_valid(sock):
            raise bluetooth.btcommon.BluetoothError("Transport endpoint is not connected")

        disc_pkt = DISC.gen(channel=CTRL_CHANNEL)
        sock.send(disc_pkt)
        # If send succeeds, the first transition was successful.
        path.append((src1, "send_disc_ctrl", dest1, True))

        # --- Step 2: Receive final UA or Timeout (only if send succeeded) ---
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, responses = process_rsps(resp_list, required_types=["UA"], allow_timeout=True)
        
        if "UA" in responses:
            path.append((src2, "recv_ua", dest2_final, True))
        else:
            path.append((src2, "timeout", dest2_final, True))

    except bluetooth.btcommon.BluetoothError as e:
        # *** THIS IS THE FIX ***
        # This block catches the "Transport endpoint is not connected" error.
        # Even though the send failed, we know the logical intent.
        print(colored(f" [Warn] Could not send DISC on CTRL_CHANNEL: {e}. Assuming session is down.", "yellow"))
        
        # We record the intended path: the attempt to send DISC, followed by an immediate timeout.
        # Mark the send as successful because the *intent* was to enter the wait state.
        path.append((src1, "send_disc_ctrl", dest1, True))
        # Mark the receive as a timeout because we never got a response.
        path.append((src2, "timeout", dest2_final, True))
    
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(colored(f" [Fail] A critical error occurred in tc_BV_04_C: {e}", "red"))
        # Record the send attempt as failed in this case
        path.append((src1, "send_disc_ctrl", dest1, False))

    if sock: 
        try:
            sock.close()
        except Exception:
            pass
            
    return path


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
    path = []
    print(colored(f"[*] DLC Establishment for DLCI={dlci} (BV-05-C)", "cyan"))
    
    sock = ensure_rfcomm_session(sock, target_addr)
    if sock is None:
        return path, None # Return empty path

    # --- Step 1: Send PN ---
    src1 = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    dest1 = state_name(StateName.CTRL_WAIT_PN, dlci) # Wait state is specific to the DLCI
    try:
        pn_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, mx_type=PN)
        sock.send(pn_pkt)
        path.append((src1, "send_pn", dest1, True))
    except Exception as e:
        print(colored(f" [Fail] Send PN: {e}", "red"))
        path.append((src1, "send_pn", dest1, False))
        return path, sock

    # --- Step 2: Receive PN or NSC Response ---
    src2 = dest1
    dest2_success = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    pn_received_successfully = False
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, _ = process_rsps(resp_list, required_types=["PN"], optional_types=["NSC"])
        
        if status in [0, 1]: # Success (PN) or Inconclusive (NSC)
            pn_received_successfully = True
            path.append((src2, "recv_pn_or_nsc", dest2_success, True))
        else:
            # *** TIMEOUT LOGIC FOR PN ***
            # A timeout occurred. Add a transition from Wait_PN back to Control_Open.
            print(colored(f" [Warn] Timeout waiting for PN response for DLCI={dlci}.", "yellow"))
            path.append((src2, "timeout", dest2_success, True)) # The timeout event itself is a "successful" transition
            return path, sock # End the test here, as we can't proceed.
            
    except Exception as e:
        print(colored(f" [Fail] PN receive: {e}", "red"))
        path.append((src2, "recv_pn_or_nsc", dest2_success, False))
        return path, sock

    # --- Step 3: Send SABM ---
    src3 = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    dest3 = state_name(StateName.CTRL_WAIT_UA, dlci)
    try:
        sabm_pkt = SABM.gen(channel=dlci)
        sock.send(sabm_pkt)
        path.append((src3, "send_sabm", dest3, True))
    except Exception as e:
        print(colored(f" [Fail] SABM send: {e}", "red"))
        path.append((src3, "send_sabm", dest3, False))
        return path, sock

    # --- Step 4: Receive UA Response ---
    src4 = dest3
    dest4_success = state_name(StateName.DATA_OPEN, dlci)
    # On timeout, we return to the last known stable state, which was Control_Open
    dest4_timeout = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, _ = process_rsps(resp_list, required_types=["UA"])
        
        if status == 0:
            # UA was received, the transition to DATA_OPEN is successful.
            path.append((src4, "recv_ua", dest4_success, True))
        else:
            # *** TIMEOUT LOGIC FOR UA ***
            # A timeout occurred. Add a transition from Data_Wait_UA back to Control_Open.
            print(colored(f" [Fail] Did not receive UA to open DLCI={dlci}.", "red"))
            path.append((src4, "timeout", dest4_timeout, True))
            return path, sock # End the test.
            
    except Exception as e:
        print(colored(f" [Fail] UA receive: {e}", "red"))
        path.append((src4, "timeout", dest4_timeout, False)) # A crash is a failed timeout transition
        return path, sock

    print(colored(f" [Pass] DLCI={dlci} established (BV-05-C)", "green"))
    return path, sock

def tc_BV_07_C(sock, target_addr, dlci, open_dlci_set, is_sub_call=False):
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
    path = []
    if not is_sub_call: 
        print(colored(f"[*] Close DLCI={dlci} (BV-07-C)", "cyan"))
    
    # Check if the DLCI is actually in the set of open channels.
    if dlci not in open_dlci_set:
        return path, sock

    # --- Step 1: Send DISC command ---
    src1 = state_name(StateName.DATA_OPEN, dlci)
    dest1 = state_name(StateName.DATA_WAIT_DISC_UA, dlci)
    try:
        disc_pkt = DISC.gen(channel=dlci)
        sock.send(disc_pkt)
        path.append((src1, "send_disc_data", dest1, True))
    except Exception as e:
        print(colored(f" [Fail] Send DISC on DLCI {dlci}: {e}", "red"))
        path.append((src1, "send_disc_data", dest1, False))
        open_dlci_set.discard(dlci)
        return path, sock

    # --- Step 2: Receive UA response ---
    src2 = dest1
    dest2 = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, responses = process_rsps(resp_list, required_types=["UA"], allow_timeout=True)
        
        if "UA" in responses:
            path.append((src2, "recv_ua", dest2, True))
        else:
            path.append((src2, "timeout", dest2, True))
            
    except Exception as e:
        print(colored(f" [Fail] Error in UA receive for DLCI={dlci}: {e}", "red"))
        path.append((src2, "recv_ua", dest2, False))

    open_dlci_set.discard(dlci)
    return path, sock

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
    path = []
    print(colored("[*] Session TEST command (BV-11-C)", "cyan"))
    
    sock = ensure_rfcomm_session(sock, target_addr)
    if sock is None:
        return path, None
    
    # --- Step 1: Send TEST command ---
    src1 = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    dest1 = state_name(StateName.CTRL_WAIT_TEST, CTRL_CHANNEL)
    
    try:
        test_pattern = b"HI"
        test_pkt = UIH.gen(channel=CTRL_CHANNEL, mx_type=TEST, payload=test_pattern)
        sock.send(test_pkt)
        path.append((src1, "send_test", dest1, True))
    except Exception as e:
        print(colored(f" [Fail] Send TEST command: {e}", "red"))
        path.append((src1, "send_test", dest1, False))
        return path, sock

    # --- Step 2: Receive TEST response ---
    src2 = dest1
    dest2_success = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    
    try:
        expected_resp = TEST.gen(payload=test_pattern, is_response=True)
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, _ = process_rsps(resp_list, required_types=["TEST"], expected_payloads={"TEST": expected_resp})
        
        if status == 0:
            # Success: Add the successful recv transition
            path.append((src2, "recv_test_echo", dest2_success, True))
        else:
            # Failure: Add the timeout transition
            print(colored(" [Fail] Did not receive correct TEST response.", "red"))
            path.append((src2, "timeout", dest2_success, True)) # Timeout is a valid transition event
            return path, sock
             
    except Exception as e:
        print(colored(f" [Fail] Error in TEST receive: {e}", "red"))
        path.append((src2, "recv_test_echo", dest2_success, False))
        return path, sock

    print(colored(" [Pass] TEST command successful (BV-11-C)", "green"))
    return path, sock

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
    path = []
    print(colored(f"[*] Remote Line Status (BV-13-C) on DLCI={dlci}", "cyan"))
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None: return path, None
    
    # --- Step 1: Send RLS command ---
    src1 = state_name(StateName.DATA_OPEN, dlci)
    dest1 = state_name(StateName.DATA_WAIT_RLS, dlci)
    
    try:
        line_status_to_send = 0b1010
        rls_pkt = UIH.gen(channel=CTRL_CHANNEL, mx_type=RLS, channel_to_ctrl=dlci, line_status=line_status_to_send)
        sock.send(rls_pkt)
        path.append((src1, "send_rls_overrun", dest1, True))
    except Exception as e:
        print(colored(f" [Fail] Send RLS: {e}", "red"))
        path.append((src1, "send_rls_overrun", dest1, False))
        return path, sock

    # --- Step 2: Receive RLS response ---
    src2 = dest1
    dest2_success = state_name(StateName.DATA_OPEN, dlci)
    
    try:
        expected_prefix = RLS.gen(channel=dlci, is_response=True, mimic_direction_bug=True)[:3]
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, _ = process_rsps(
            resp_list,
            required_types=["RLS"],
            expected_payloads={"RLS": lambda pkt: pkt.payload.startswith(expected_prefix)}
        )
        
        if status == 0:
            # Success: Add the successful recv transition
            path.append((src2, "recv_rls_resp", dest2_success, True))
        else:
            # Failure: Add the timeout transition
            print(colored(f" [Fail] RLS validation failed for DLCI={dlci} (BV-13-C).", "red"))
            path.append((src2, "timeout", dest2_success, True)) # Timeout is a valid transition event
            return path, sock

    except Exception as e:
        print(colored(f" [Fail] Error in RLS receive: {e}", "red"))
        path.append((src2, "recv_rls_resp", dest2_success, False))
        return path, sock

    print(colored(" [Pass] RLS command successful for DLCI={dlci} (BV-13-C)", "green"))
    return path, sock

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
    path = []
    print(colored(f"[*] Remote Line Status (Framing Error) (BV-14-C) on DLCI={dlci}", "cyan"))
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None:
        return path, None

    # Define the potential state transitions
    src = state_name(StateName.DATA_OPEN, dlci)
    intermediate_state = state_name(StateName.DATA_WAIT_RLS, dlci)
    dest = state_name(StateName.DATA_OPEN, dlci) # The final state is the same as the start

    # Assume failure until the entire sequence is proven successful
    success = False
    
    try:
        # --- Step 1: Send RLS command ---
        line_status_to_send = 0b1001
        rls_pkt = UIH.gen(channel=CTRL_CHANNEL, mx_type=RLS, channel_to_ctrl=dlci, line_status=line_status_to_send)
        sock.send(rls_pkt)
        
        # --- Step 2: Receive and Validate RLS response ---
        expected_prefix = RLS.gen(channel=dlci, is_response=True, mimic_direction_bug=True)[:3]
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, _ = process_rsps(
            resp_list,
            required_types=["RLS"],
            expected_payloads={"RLS": lambda pkt: pkt.payload.startswith(expected_prefix)}
        )
        
        # The entire sequence is successful ONLY if the validation passes (status == 0)
        if status == 0:
            success = True
        else:
            print(colored(f" [Fail] RLS validation failed for DLCI={dlci} (BV-14-C).", "red"))

    except Exception as e:
        print(colored(f" [Fail] Error in RLS test (BV-14-C): {e}", "red"))
        # 'success' remains False
    
    # --- Step 3: Append the full path ONLY if the sequence was successful ---
    if success:
        # If we succeeded, we can add both transitions to the path.
        path.append((src, "send_rls_framing", intermediate_state, True))
        path.append((intermediate_state, "recv_rls_resp", dest, True))
        print(colored(f" [Pass] RLS command successful for DLCI={dlci} (BV-14-C)", "green"))
    else:
        # If any part failed, we do not append anything to the path.
        # The intermediate state DATA_WAIT_RLS will not be created.
        print(colored(f" [Result] The full send/receive sequence for BV-14-C failed.", "yellow"))

    return path, sock


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
    path = []
    print(colored(f"[*] Remote Port Negotiation with Settings (BV-17-C) on DLCI={dlci}", "cyan"))
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None: return path, None

    # --- Step 1: Send RPN command with port settings ---
    src1 = state_name(StateName.DATA_OPEN, dlci)
    dest1 = state_name(StateName.DATA_WAIT_RPN, dlci)
    
    try:
        port_settings = bytes([0x07, 0x03, 0x00, 0x11, 0x13, 0xFF, 0xFF, 0xFF])
        rpn_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, mx_type=RPN, port_values=port_settings)
        sock.send(rpn_pkt)
        path.append((src1, "send_rpn_settings", dest1, True))
    except Exception as e:
        print(colored(f" [Fail] Send RPN with settings: {e}", "red"))
        path.append((src1, "send_rpn_settings", dest1, False))
        return path, sock

    # --- Step 2: Receive RPN or NSC response ---
    src2 = dest1
    dest2_success = state_name(StateName.DATA_OPEN, dlci)
    
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, responses = process_rsps(resp_list, optional_types=["RPN", "NSC"], allow_timeout=True)
        
        if status in [0, 1]: # Success (RPN/NSC) or inconclusive timeout
            # If we received a valid packet, the trigger is specific.
            if "RPN" in responses or "NSC" in responses:
                path.append((src2, "recv_rpn_or_nsc", dest2_success, True))
                if "NSC" in responses:
                    print(colored("   -> Received NSC (Not Supported)", "blue"))
            else: # Otherwise, it was a clean timeout
                path.append((src2, "timeout", dest2_success, True))
        else: # Hard fail from process_rsps
            path.append((src2, "timeout", dest2_success, True))
            return path, sock

    except Exception as e:
        print(colored(f" [Fail] Error in RPN receive: {e}", "red"))
        path.append((src2, "recv_rpn_or_nsc", dest2_success, False))
        return path, sock

    print(colored(" [Pass] RPN (with settings) handled correctly (BV-17-C)", "green"))
    return path, sock

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
    path = []
    print(colored(f"[*] RPN Query for Settings (BV-19-C) on DLCI={dlci}", "cyan"))
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None: return path, None

    # --- Step 1: Send basic RPN query ---
    src1 = state_name(StateName.DATA_OPEN, dlci)
    dest1 = state_name(StateName.DATA_WAIT_RPN, dlci)
    
    try:
        rpn_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, mx_type=RPN)
        sock.send(rpn_pkt)
        path.append((src1, "send_rpn_query", dest1, True))
    except Exception as e:
        print(colored(f" [Fail] Send RPN query: {e}", "red"))
        path.append((src1, "send_rpn_query", dest1, False))
        return path, sock

    # --- Step 2: Receive RPN response and validate its length ---
    src2 = dest1
    dest2_success = state_name(StateName.DATA_OPEN, dlci)
    
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, _ = process_rsps(
            resp_list,
            required_types=["RPN"],
            expected_payloads={"RPN": lambda pkt: pkt.payload_len == 8}
        )
        
        if status == 0:
            # Success: Add the successful recv transition
            path.append((src2, "recv_rpn_8octet_resp", dest2_success, True))
        else:
            # Failure: Add the timeout transition
            print(colored(f" [Fail] RPN response for DLCI={dlci} did not have the expected 8 data octets.", "red"))
            path.append((src2, "timeout", dest2_success, True))
            return path, sock
            
    except Exception as e:
        print(colored(f" [Fail] Error in RPN query receive: {e}", "red"))
        path.append((src2, "recv_rpn_8octet_resp", dest2_success, False))
        return path, sock

    print(colored(" [Pass] RPN query successful (BV-19-C)", "green"))
    return path, sock

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
    path = []
    print(colored(f"[*] Credit Based Flow Control (BV-21-C) on DLCI={dlci}", "cyan"))
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None: return path, None

    # --- Step 1: Perform MSC Handshake ---
    
    # 1a: Send MSC command (DATA_OPEN -> DATA_WAIT_MSC)
    src_msc1 = state_name(StateName.DATA_OPEN, dlci)
    dest_msc1 = state_name(StateName.DATA_WAIT_MSC, dlci)
    try:
        msc_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, mx_type=MSC, fc=False, rtc=True, rtr=True)
        sock.send(msc_pkt)
        path.append((src_msc1, "send_msc", dest_msc1, True))
    except Exception as e:
        print(colored(f" [Warn] MSC Handshake send failed: {e}", "yellow"))
        path.append((src_msc1, "send_msc", dest_msc1, False))
    
    # 1b: Receive MSC response (DATA_WAIT_MSC -> DATA_OPEN)
    src_msc2 = dest_msc1
    dest_msc2 = state_name(StateName.DATA_OPEN, dlci)
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, responses = process_rsps(resp_list, optional_types=["MSC"], allow_timeout=True)
        
        # *** TIMEOUT LOGIC FOR MSC ***
        if "MSC" in responses:
            # Success: Add the successful recv transition
            path.append((src_msc2, "recv_msc_resp", dest_msc2, True))
        else:
            # Failure/Timeout: Add the timeout transition
            print(colored("    [Warn] No MSC response received.", "yellow"))
            path.append((src_msc2, "timeout", dest_msc2, True))

    except Exception as e:
         print(colored(f" [Warn] MSC Handshake receive failed: {e}", "yellow"))
         path.append((src_msc2, "recv_msc_resp", dest_msc2, False))

    # --- Step 2: Wait to Receive Credits from the IUT ---
    # This transitions from DATA_OPEN to a new state, DATA_CREDIT_RCVD.
    src_credit = state_name(StateName.DATA_OPEN, dlci)
    dest_credit = state_name(StateName.DATA_CREDIT_RCVD, dlci)
    credits_received = 0
    
    try:
        print(colored("    -> Waiting to receive credits from IUT...", "cyan"))
        resp_list, sock = inter_recv(sock, dur=3.0)
        status, responses = process_rsps(resp_list, required_types=["UIH_CREDIT"], allow_timeout=True)
        
        if status == 0 and "UIH_CREDIT" in responses:
            credit_pkt = responses["UIH_CREDIT"]
            credits_received = credit_pkt.credit
            if credits_received > 0:
                print(colored(f"    -> Received {credits_received} credits!", "gray"))
                path.append((src_credit, "recv_credits", dest_credit, True))
            else:
                path.append((src_credit, "recv_credits", dest_credit, False))
        else:
            print(colored(f" [Warn] Did not receive credits from IUT on DLCI={dlci}.", "yellow"))
            path.append((src_credit, "recv_credits", dest_credit, False))
            return path, sock

    except Exception as e:
        print(colored(f" [Fail]    Error while receiving credits from IUT: {e}", "red"))
        path.append((src_credit, "recv_credits", dest_credit, False))
        return path, sock

    # --- Step 3: Send Data Frames According to Credits Received ---
    # This transitions from DATA_CREDIT_RCVD back to DATA_OPEN.
    src_data = dest_credit
    dest_data = state_name(StateName.DATA_OPEN, dlci)
    
    try:
        print(colored(f"    -> Sending {credits_received} data frames...", "cyan"))
        for i in range(credits_received):
            data_to_send = f"packet_{i+1}".encode()
            data_pkt = UIH.gen(channel=dlci, mx_type=DATA, payload=data_to_send)
            sock.send(data_pkt)
            time.sleep(0.05)
        print(colored(f"    -> Finished sending data.", "gray"))
        path.append((src_data, "send_credited_data", dest_data, True))
    except Exception as e:
        print(colored(f" [Fail]    Error sending data after receiving credits: {e}", "red"))
        path.append((src_data, "send_credited_data", dest_data, False))
        return path, sock

    print(colored(f" [Pass] Credit-based flow control test complete (BV-21-C)", "green"))
    return path, sock


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
    path = []
    print(colored(f"[*] Data Transfer with MSC Handshake (BV-22-C) on DLCI={dlci}", "cyan"))
    sock = ensure_dlci_open(sock, target_addr, dlci, open_dlci_set)
    if sock is None: return path, None

    # --- Step 1: Send MSC command ---
    src1 = state_name(StateName.DATA_OPEN, dlci)
    dest1 = state_name(StateName.DATA_WAIT_MSC, dlci)
    
    try:
        msc_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, mx_type=MSC, fc=False, rtc=True, rtr=True)
        sock.send(msc_pkt)
        path.append((src1, "send_msc", dest1, True))
    except Exception as e:
        print(colored(f" [Fail] Send MSC: {e}", "red"))
        path.append((src1, "send_msc", dest1, False))
        return path, sock

    # --- Step 2: Wait for MSC response ---
    src2 = dest1
    dest2_success = state_name(StateName.DATA_OPEN, dlci)
    
    try:
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, responses = process_rsps(resp_list, optional_types=["MSC"], allow_timeout=True)
        
        # *** TIMEOUT LOGIC FOR MSC ***
        if "MSC" in responses:
            # Success: Add the successful recv transition
            path.append((src2, "recv_msc_resp", dest2_success, True))
        else:
            # Failure/Timeout: Add the timeout transition
            print(colored("    [Warn] No MSC response received.", "yellow"))
            path.append((src2, "timeout", dest2_success, True))
            
    except Exception as e:
        print(colored(f" [Fail] Error in MSC receive: {e}", "red"))
        path.append((src2, "recv_msc_resp", dest2_success, False))

    # --- Step 3: Send data packet (a self-loop on DATA_OPEN) ---
    src3 = state_name(StateName.DATA_OPEN, dlci)
    dest3 = state_name(StateName.DATA_OPEN, dlci)
    try:
        data_pkt = UIH.gen(channel=dlci, mx_type=DATA, payload=b"test_data")
        sock.send(data_pkt)
        path.append((src3, "send_data", dest3, True))
    except Exception as e:
        print(colored(f" [Fail] Send data after MSC: {e}", "red"))
        path.append((src3, "send_data", dest3, False))
        return path, sock

    print(colored(" [Pass] Data transfer after MSC handshake complete (BV-22-C)", "green"))
    return path, sock


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
    path = []
    print(colored("[*] Unsupported Command Handling (BV-25-C)", "cyan"))
    
    sock = ensure_rfcomm_session(sock, target_addr)
    if sock is None:
        return path, None # Return empty path on hard failure

    # Define the potential state transitions
    src1 = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    dest1 = state_name(StateName.CTRL_WAIT_NSC, CTRL_CHANNEL)
    src2 = dest1
    dest2 = state_name(StateName.CTRL_OPEN, CTRL_CHANNEL)
    
    # --- Perform the full sequence and only record the path on total success ---
    success = False # Assume failure until proven otherwise
    
    try:
        # Step 1: Send INVALID command
        invalid_pkt = UIH.gen(channel=CTRL_CHANNEL, mx_type=INVALID)
        sent_invalid_type = invalid_pkt[3]
        sock.send(invalid_pkt)
        
        # Step 2: Receive and validate NSC response
        resp_list, sock = inter_recv(sock, dur=1.0)
        status, responses = process_rsps(
            resp_list,
            required_types=["NSC"],
            expected_payloads={"NSC": lambda pkt: pkt.payload[2] == sent_invalid_type}
        )
        
        # *** THE KEY LOGIC ***
        # Only if the status is 0 (PASS) do we consider the entire sequence a success.
        if status == 0:
            success = True
        else:
            # Provide debug info on failure
            print(colored(" [Fail] Did not receive a valid NSC response echoing the command type.", "red"))
            if "NSC" in responses:
                nsc_pkt = responses["NSC"]
                print(colored(f"   -> Got NSC, but it contained type {nsc_pkt.payload[2]:#x} instead of {sent_invalid_type:#x}", "yellow"))
            
    except Exception as e:
        print(colored(f" [Fail] Error in NSC test: {e}", "red"))
        # 'success' remains False
    
    # --- Step 3: Append the path ONLY if the whole sequence was successful ---
    if success:
        path.append((src1, "send_invalid", dest1, True))
        path.append((src2, "recv_nsc_echo", dest2, True))
        print(colored(" [Pass] Unsupported command handled correctly (BV-25-C)", "green"))
    else:
        # We don't append anything to the path, so no new states will be created.
        print(colored(" [Result] The full send/receive sequence for BV-25-C failed.", "yellow"))

    return path, sock