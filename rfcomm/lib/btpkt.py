import bluetooth
from termcolor import colored
from functools import wraps
import errno
import os
import signal
import time

from layer.rfcomm.const import RFCOMM_CONTROL, MX_TYPE

RFCOMM_EA = 1
MTU = 0xffff

def _pf(const):
    # This function is correct. It sets the Poll/Final bit.
    return const | (1 << 4)

def mx_type_mask(x):
    # This correctly ignores the C/R bit for multiplexer commands.
    return x & 0b11111101

def frame_type_mask(x):
    # This ignores the Poll/Final bit (bit 4) for standard RFCOMM frames.
    return x & 0b11101111

class FRAME_PKT:
    def __init__(self, pkt):
        self.pkt = pkt
        self.address = ""
        self.control = ""
        self.length = ""
        self.payload = b''
        self.payload_len = 0
        self.credit = 0  # <-- NEW attribute to store credits

    def parse_pkt(self):
        """
        A robust parser that identifies UIH frames carrying credits.
        """
        if not self.pkt or len(self.pkt) < 2:
            return None
        
        self.address = self.pkt[0]
        self.control = self.pkt[1]
        
        # Mask the control byte to ignore the P/F bit for standard comparisons.
        masked_control = frame_type_mask(self.control)
        
        if masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_SABM):
            return 'SABM'
        elif masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_UA):
            return 'UA'
        elif masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_DISC):
            return 'DISC'
        elif masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_DM):
            return 'DM'

        # --- NEW LOGIC: Specifically check for UIH with P/F bit first ---
        # A UIH frame with the P/F bit set is used exclusively for credit-based flow control.
        elif self.control == _pf(RFCOMM_CONTROL.RC_CONTROL_UIH):
            # This is a UIH frame carrying credits.
            # The credit value is the first byte of the information field.
            info_start_offset = 3
            if len(self.pkt) > info_start_offset:
                self.credit = self.pkt[info_start_offset]
            return 'UIH_CREDIT' # Return a unique type to identify this frame

        # --- EXISTING LOGIC for standard UIH frames ---
        elif masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_UIH):
            # Standard UIH frame, now parse the inner multiplexer command or data.
            mx_start_offset = 3
            if len(self.pkt) > mx_start_offset:
                self.payload = self.pkt[mx_start_offset:-1] # Multiplexer payload
                
                # Check if it's a multiplexer command or just data
                if len(self.payload) > 1:
                    self.payload_len = self.payload[1] >> 1
                    masked_mx = mx_type_mask(self.payload[0])

                    if masked_mx == mx_type_mask(MX_TYPE.MX_PN): return 'PN'
                    elif masked_mx == mx_type_mask(MX_TYPE.MX_TEST): return 'TEST'
                    elif masked_mx == mx_type_mask(MX_TYPE.MX_MSC): return 'MSC'
                    elif masked_mx == mx_type_mask(MX_TYPE.MX_FCON): return 'FCON'
                    elif masked_mx == mx_type_mask(MX_TYPE.MX_FCOFF): return 'FCOFF'
                    elif masked_mx == mx_type_mask(MX_TYPE.MX_RPN): return 'RPN'
                    elif masked_mx == mx_type_mask(MX_TYPE.MX_RLS): return 'RLS'
                    elif masked_mx == mx_type_mask(MX_TYPE.MX_NSC): return 'NSC'
                    else: 
                        # If not a known MX type, it's a simple data frame.
                        return 'UIH_DATA'
                else:
                    # If payload is 1 byte or less, it's likely just data.
                    return 'UIH_DATA'
            else:
                return 'UIH' # UIH with no payload
        else:
            return None # Unknown frame type

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL,seconds) #used timer instead of alarm
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wraps(func)(wrapper)
    return decorator

def inter_recv(sock, dur=None):
    """
    If dur is None: Receive a single packet (same as original inter_recv).
    If dur is float: Receive all packets arriving within the duration and return as a list.
    """
    if dur is None:
        conn_rsp = sock.recv(MTU)
        return conn_rsp, sock
    else:
        # For 'dur' seconds, repeatedly receive packets and store them in a list
        end_time = time.time() + dur
        result_list = []
        sock.setblocking(False)
        try:
            while time.time() < end_time:
                try:
                    conn_rsp = sock.recv(MTU)
                    if not conn_rsp:
                        break
                    result_list.append(conn_rsp)
                except (bluetooth.btcommon.BluetoothError, BlockingIOError):
                    # If no data is available, wait briefly to prevent busy-waiting
                    time.sleep(0.01)
        finally:
            sock.setblocking(True)
        return result_list, sock

# def process_rsps(resp_list):
#     """
#     Given a list of respS,
#     returns a list of (resp, res) where res is not None
#     (res = FRAME_PKT(resp).parse_pkt()).
#     """
#     results = []
#     for resp in resp_list:
#         frame_pkt = FRAME_PKT(resp)
#         res = frame_pkt.parse_pkt()
#         if res is not None:
#             results.append(res)
#     return results


# Helper function for parsing RLS payload (13_C and 14_C)
def compare_rls_payload(actual, expected, length=3):
    return actual[:length] == expected[:length]

def process_rsps(
    resp_list,
    required_types=None,
    optional_types=None,
    expected_payloads=None,
    allow_timeout=False
):
    """
    Validates parsed RFCOMM packets.

    Args:
        resp_list: List of raw packets.
        required_types: List of required packet types.
        optional_types: List of optional packet types.
        expected_payloads: Dict mapping type to expected value or validator function.
        allow_timeout: If True, missing responses may be inconclusive.

    Returns:
        Tuple[int, dict]: (status_code, {pkt_type: pkt_instance})
            -1: FAIL
             0: PASS
             1: INCONCLUSIVE
    """
    if not resp_list:
        if allow_timeout:
            print(colored(" [Inconclusive] No response received, but timeout is allowed.", "yellow"))
            return 1, {}
        else:
            print(colored(" [Fail] No response received and timeout is not allowed.", "red"))
            return -1, {}

    result = {}
    for raw_pkt in resp_list:
        pkt = FRAME_PKT(raw_pkt)
        pkt_type = pkt.parse_pkt()
        if pkt_type is None or pkt_type in result:
            continue
        result[pkt_type] = pkt

    # 1. Check for required types
    if required_types:
        for rtype in required_types:
            if rtype not in result:
                print(colored(f" [Fail] Required packet '{rtype}' not received.", "red"))
                return -1, result
            else:
                print(colored(f" [Pass] Required packet '{rtype}' received.", "green"))

    # 2. Validate payloads (supports lambda/callable for custom validation)
    if expected_payloads:
        for pkt_type, expected in expected_payloads.items():
            if pkt_type not in result:
                print(colored(f" [Fail] Expected payload for '{pkt_type}' not received.", "red"))
                return -1, result
            actual = result[pkt_type].payload
            if callable(expected):
                if not expected(actual):
                    print(colored(f" [Fail] Payload for '{pkt_type}' did not pass the validator.", "red"))
                    return -1, result
                else:
                    print(colored(f" [Pass] Payload for '{pkt_type}' passed custom validator.", "green"))
            else:
                if actual != expected:
                    print(colored(f" [Fail] Payload mismatch in '{pkt_type}'.", "red"))
                    return -1, result
                else:
                    print(colored(f" [Pass] Payload for '{pkt_type}' matched.", "green"))

    # 3. Handle optional types (if no required types given)
    if not required_types and optional_types:
        matched = any(t in result for t in optional_types)
        if matched:
            print(colored(" [Inconclusive] Only optional response received (no required types specified).", "yellow"))
            return 1, result
        else:
            if allow_timeout:
                print(colored(" [Inconclusive] No optional response received, but timeout is allowed.", "yellow"))
                return 1, result
            else:
                print(colored(" [Fail] Optional response not received and timeout is not allowed.", "red"))
                return -1, result

    # All checks passed
    return 0, result