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
    return const | (1 << 4)

def mx_type_mask(x):
    return x & 0b11111101

def frame_type_mask(x):
    return x & 0b11101111

class FRAME_PKT:
    # This class is correct and does not need changes.
    def __init__(self, pkt):
        self.pkt = pkt
        self.address = ""
        self.control = ""
        self.payload = b''
        self.payload_len = 0
        self.credit = 0

    def parse_pkt(self):
        # This method is correct and does not need changes.
        if not self.pkt or len(self.pkt) < 2: return None
        self.address = self.pkt[0]
        self.control = self.pkt[1]
        masked_control = frame_type_mask(self.control)
        if masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_SABM): return 'SABM'
        elif masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_UA): return 'UA'
        elif masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_DISC): return 'DISC'
        elif masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_DM): return 'DM'
        elif self.control == _pf(RFCOMM_CONTROL.RC_CONTROL_UIH):
            info_start_offset = 3
            if len(self.pkt) > info_start_offset: self.credit = self.pkt[info_start_offset]
            return 'UIH_CREDIT'
        elif masked_control == frame_type_mask(RFCOMM_CONTROL.RC_CONTROL_UIH):
            mx_start_offset = 3
            if len(self.pkt) > mx_start_offset:
                self.payload = self.pkt[mx_start_offset:-1]
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
                    else: return 'UIH_DATA'
                else: return 'UIH_DATA'
            else: return 'UIH'
        else: return None

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    # This decorator is correct and does not need changes.
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)
        @wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL,seconds)
            try: result = func(*args, **kwargs)
            finally: signal.alarm(0)
            return result
        return wrapper
    return decorator

def inter_recv(sock, dur=None):
    # This function is correct and does not need changes.
    if dur is None:
        try:
            conn_rsp = sock.recv(MTU)
            return [conn_rsp], sock
        except:
             return [], sock
    else:
        end_time = time.time() + dur
        result_list = []
        sock.setblocking(False)
        try:
            while time.time() < end_time:
                try:
                    conn_rsp = sock.recv(MTU)
                    if not conn_rsp: break
                    result_list.append(conn_rsp)
                except (bluetooth.btcommon.BluetoothError, BlockingIOError):
                    time.sleep(0.01)
        finally:
            sock.setblocking(True)
        return result_list, sock

def process_rsps(
    resp_list,
    required_types=None,
    optional_types=None,
    expected_payloads=None,
    allow_timeout=False
):
    """
    Validates parsed RFCOMM packets.
    """
    if not resp_list:
        if allow_timeout:
            return 1, {}
        else:
            print(colored(" [Fail] No response received and timeout is not allowed.", "red"))
            return -1, {}

    result = {}
    for raw_pkt in resp_list:
        pkt = FRAME_PKT(raw_pkt)
        pkt_type = pkt.parse_pkt()
        if pkt_type and pkt_type not in result:
            result[pkt_type] = pkt

    if required_types:
        for rtype in required_types:
            if rtype not in result:
                print(colored(f" [Fail] Required packet '{rtype}' not received.", "red"))
                return -1, result

    if expected_payloads:
        for pkt_type, validator in expected_payloads.items():
            if pkt_type not in result:
                print(colored(f" [Fail] Expected payload for '{pkt_type}' not received.", "red"))
                return -1, result
            
            # *** THIS IS THE FIX ***
            # Instead of passing just the payload, we pass the entire FRAME_PKT object.
            pkt_object_to_validate = result[pkt_type]
            
            if callable(validator):
                # The lambda function (validator) will now receive the whole packet object.
                if not validator(pkt_object_to_validate):
                    print(colored(f" [Fail] Custom validation for '{pkt_type}' failed.", "red"))
                    return -1, result
            else:
                # The default behavior is still to compare the raw payload bytes.
                if pkt_object_to_validate.payload != validator:
                    print(colored(f" [Fail] Payload mismatch in '{pkt_type}'.", "red"))
                    return -1, result

    # Simplified the remaining logic for clarity and correctness
    final_status = 0
    if not required_types and optional_types:
        if not any(t in result for t in optional_types):
            final_status = 1 if allow_timeout else -1
            
    # Return the full dictionary of parsed packets for potential use in the test case
    return final_status, result