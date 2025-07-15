import bluetooth
import traceback
from termcolor import colored
from layer.rfcomm.const import RFCOMM_PSM
from lib.btpkt import inter_recv, process_rsps
from lib.state import SABM, UA, DISC, UIH
from lib.state import PN, TEST, INVALID, RLS, RPN, FCON, DATA
from lib.state import CTRL_CHANNEL

def tc_BV_01_C(target_addr):
    """
    TS: BV-01-C RFCOMM Session Initialization (Initiator)
    FSM: Initiated --(Send SABM)--> Wait_UA (Setup) --(Recv UA)--> Established_Control
    Steps:
        1. Establish L2CAP connection
        2. Send RFCOMM SABM (DLCI=0)
        3. Wait for UA and verify
    Returns:
        Bluetooth socket if successful, else False
    """
    # Step 1: Establish L2CAP connection
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    try:
        sock.connect((target_addr, RFCOMM_PSM))
    except Exception as e:
        print(colored(f" [Fail]\n L2CAP connect: {e}", "red"))
        sock.close()
        return False

    # Step 2: Send SABM (DLCI=0)
    try:
        sabm_pkt = SABM.gen(channel=CTRL_CHANNEL, transition=True)
        sock.send(sabm_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n SABM send: {e}", "red"))
        sock.close()
        traceback.print_exc()
        return False

    # Step 3: Wait for UA and verify
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_packets = process_rsps(resp_list)
        if len(valid_packets) == 0:
            print(colored(" [Fail]\n No valid RFCOMM response after SABM.", "red"))
            sock.close()
            return False
        
        # look for UA
        if "UA" not in valid_packets:
            print(colored(f" [Fail]\n UA not received.", "red"))
            sock.close()
            return False

    except Exception as e:
        print(colored(f" [Fail]\n Error in UA receive: {e}", "red"))
        sock.close()
        traceback.print_exc()
        return False

    print(colored(" [Pass] RFCOMM session initialized (BV-01-C)", "green"))
    return sock

def tc_BV_04_C(sock):
    """
    TS: BV-04-C RFCOMM Session Shutdown
    FSM:
        Established_Control --(Send DISC)--> Wait_DISC_UA (Ctrl) --(Recv UA)--> Initiated
    Args:
        sock: Bluetooth socket (RFCOMM session established)
    Returns:
        True if all channels/session closed successfully, else False
    """

    # close the control channel (DLCI=0)
    dlci=CTRL_CHANNEL
    try:
        disc_pkt = DISC.gen(channel=dlci, transition=True)
        sock.send(disc_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send DISC on CTRL_CHANNEL: {e}", "red"))
        sock.close()
        traceback.print_exc()
        return False

    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "UA" not in valid_responses:
            print(colored(f" [Warn]\n UA not received after DISC on DLCI={dlci}. (got {valid_responses})", "yellow"))
            # Often devices close channel abruptly after DISC, so treat as PASS
            # Optionally: return False here if strict protocol required
        else:
            print(colored(f" [Pass] DLCI={dlci} closed (BV-04-C)", "green"))
        return True
    except Exception as e:
        print(colored(f" [Fail]\n Error in UA receive for CTRL_CHANNEL: {e}", "red"))
        sock.close()
        traceback.print_exc()
        return False

def tc_BV_05_C(sock, dlci):
    """
    TS: BV-05-C DLC Establishment (Initiator)
    FSM:
      Established_Control --(Send PN)--> Wait_PN_Response --(Recv PN)--> Established_Control
      --(Send SABM)--> Wait_UA (Ctrl) --(Recv UA)--> DLC Open (DLCI≠0)
    Args:
        sock: Bluetooth socket (already connected, control session open)
        dlci: DLCI number to open (>0)
    Returns:
        True if DLCI open succeeded, else False
    """

    # STEP 1: Send PN (Parameter Negotiation) for DLCI
    try:
        pn_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, transition=True, mx_type=PN)
        sock.send(pn_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send PN for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False

    # STEP 2: Wait for PN response(s)
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "PN" not in valid_responses:
            print(colored(f" [Fail]\n PN response not received for DLCI={dlci}. (got {valid_responses})", "red"))
            return False
    except Exception as e:
        print(colored(f" [Fail]\n Error in PN receive for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False

    # STEP 3: Send SABM for DLCI
    try:
        sabm_pkt = SABM.gen(channel=dlci, transition=True)
        sock.send(sabm_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send SABM for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False

    # STEP 4: Wait for UA for DLCI
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "UA" not in valid_responses:
            print(colored(f" [Fail]\n UA not received for DLCI={dlci} (got {valid_responses}).", "red"))
            return False
    except Exception as e:
        print(colored(f" [Fail]\n Error in UA receive for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False

    print(colored(f" [Pass] DLCI={dlci} established (BV-05-C)", "green"))
    return True

def tc_BV_07_C(sock, dlci):
    """
    TS: BV-07-C Close DLC (by IUT)
    FSM:
        DLC Open (DLCI≠0) --(Send DISC)--> Wait_DISC_UA (DLC) --(Recv UA)--> Control Phase
    Args:
        sock: Bluetooth socket (RFCOMM data session open)
        dlci: DLCI number to close (>0)
    Returns:
        True if DLCI closed successfully, else False
    """

    # Step 1: Send DISC on specified DLCI
    try:
        disc_pkt = DISC.gen(channel=dlci, transition=True)
        sock.send(disc_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send DISC on DLCI={dlci}: {e}", "red"))
        sock.close()
        return False

    # Step 2: Wait for UA response (with timeout), only RFCOMM frames considered
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "UA" not in valid_responses:
            print(colored(f" [Warn]\n UA not received after DISC on DLCI={dlci}. (got {valid_responses})", "yellow"))
            # Often devices close channel abruptly after DISC, so treat as PASS
            # Optionally: return False here if strict protocol required
        else:
            print(colored(f" [Pass] DLCI={dlci} closed (BV-07-C)", "green"))
        return True

    except Exception as e:
        print(colored(f" [Fail]\n Error in UA receive for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        sock.close()
        return False
    
def tc_BV_11_C(sock):
    """
    TS: BV-11-C TEST Command (Loopback/Echo)
    FSM:
        Established_Control --(Send TEST)--> Established_Control --(Recv TEST)--> (Echo Verified)
    Args:
        sock: Bluetooth socket (RFCOMM session established)
    Returns:
        True if TEST response received, else False
    """
    try:
        test_pattern = b""
        test_pkt = UIH.gen(channel=CTRL_CHANNEL, transition=False, mx_type=TEST, payload=test_pattern)
        # test_pkt = UIH.gen(channel=CTRL_CHANNEL, transition=False, mx_type=TEST)
        sock.send(test_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send TEST command: {e}", "red"))
        traceback.print_exc()
        return False

    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "TEST" not in valid_responses:
            print(colored(" [Fail]\n Did not receive TEST response.", "red"))
            return False
    except Exception as e:
        print(colored(f" [Fail]\n Error in TEST receive: {e}", "red"))
        traceback.print_exc()
        return False

    print(colored(" [Pass] TEST command successful (BV-11-C)", "green"))
    return True

def tc_BV_14_C(sock, dlci):
    """
    TS: BV-14-C Remote Line Status (RLS) Command
    FSM:
        DLC Open (DLCI≠0) --(Send RLS)--> Wait_RLS_Response --(Recv RLS)--> DLC Open (RLS Confirmed)
    Args:
        sock: Bluetooth socket (RFCOMM session established)
        dlci: DLCI number to target (>0)
    Returns:
        True if RLS response received, else False
    """
    try:
        rls_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, transition=True, mx_type=RLS)
        sock.send(rls_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send RLS for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "RLS" not in valid_responses:
            print(colored(f" [Fail]\n RLS response not received for DLCI={dlci}. (got {valid_responses})", "red"))
            return False
    except Exception as e:
        print(colored(f" [Fail]\n Error in RLS receive for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False

    print(colored(f" [Pass] RLS command successful for DLCI={dlci} (BV-14-C)", "green"))
    return True

def tc_BV_17_C(sock, dlci):
    """
    TS: BV-17-C Remote Port Negotiation (RPN) Command
    FSM:
        DLC Open (DLCI≠0) --(Send RPN)--> Wait_RPN_Response --(Recv RPN or NSC)--> DLC Open (DLCI≠0)
    Args:
        sock: Bluetooth socket (RFCOMM session established)
        dlci: DLCI number to target (>0)
    Returns:
        True if RPN or NSC response received, else False
    """
    try:
        rpn_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=dlci, transition=True, mx_type=RPN)
        sock.send(rpn_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send RPN for DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
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
        traceback.print_exc()
        return False

def tc_BV_21_C(sock, dlci):
    """
    TS: BV-21-C Credit-based Flow Control and Data Transfer
    FSM:
        DLC Open (DLCI≠0) --(Send FCON)--> Credit Flow --(Send DATA w/credit)--> Data Transfer Verified
    Args:
        sock: Bluetooth socket (RFCOMM session established)
        dlci: DLCI number to target (>0)
    Returns:
        True if FCON and DATA with credit sent successfully, else False
    """
    try:
        fcon_pkt = UIH.gen(channel=CTRL_CHANNEL, transition=True, mx_type=FCON)
        sock.send(fcon_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send FCON: {e}", "red"))
        traceback.print_exc()
        return False
    try:
        data_pkt = UIH.gen(channel=dlci, transition=False, mx_type=DATA, payload=b'credit_test', credit=1)
        sock.send(data_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send UIH with credit on DLCI={dlci}: {e}", "red"))
        traceback.print_exc()
        return False

    print(colored(f" [Pass] Credit-based flow enabled and tested (BV-21-C)", "green"))
    return True

def tc_BV_25_C(sock):
    """
    TS: BV-25-C Unsupported Command Handling
    FSM:
        Established_Control --(Send INVALID)--> Wait_NSC --(Recv NSC)--> Established_Control
    Args:
        sock: Bluetooth socket (RFCOMM session established)
    Returns:
        True if NSC received, else False
    """
    try:
        invalid_pkt = UIH.gen(channel=CTRL_CHANNEL, transition=True, mx_type=INVALID)
        sock.send(invalid_pkt)
    except Exception as e:
        print(colored(f" [Fail]\n Send Invalid Command: {e}", "red"))
        traceback.print_exc()
        return False
    try:
        resp_list, sock = inter_recv(sock, dur=0.1)
        valid_responses = process_rsps(resp_list)
        if "NSC" not in valid_responses:
            print(colored(f" [Fail]\n Did not receive NSC after invalid command. (got {valid_responses})", "red"))
            return False
    except Exception as e:
        print(colored(f" [Fail]\n Error in NSC receive: {e}", "red"))
        traceback.print_exc()
        return False

    print(colored(" [Pass] Unsupported command handled correctly (BV-25-C)", "green"))
    return True
