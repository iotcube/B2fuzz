import bluetooth
from scapy.packet import Packet
import random

# for time out recv
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

# Mask to ignore C/R bit (bit 1)
def mx_type_mask(x):
    return x & 0b11111101

class FRAME_PKT:
    def __init__(self, pkt):
        self.pkt = pkt
        self.address = ""
        self.control = ""
        self.length = ""
        self.frame_check_seq = ""
        self.mx_type = None      # For UIH subcommand type
    
    # def parse_pkt(self):
    #     self.address = self.pkt[0]
    #     self.control = self.pkt[1]
    #     if self.control == RFCOMM_CONTROL.RC_CONTROL_DISC or _pf(RFCOMM_CONTROL.RC_CONTROL_DISC) == self.control:
    #         return 'DISC'
    #     elif self.control == RFCOMM_CONTROL.RC_CONTROL_DM or _pf(RFCOMM_CONTROL.RC_CONTROL_DM) == self.control:
    #         return 'DM'
    #     elif self.control == RFCOMM_CONTROL.RC_CONTROL_SABM or _pf(RFCOMM_CONTROL.RC_CONTROL_SABM) == self.control:
    #         return 'SABM'
    #     elif self.control == RFCOMM_CONTROL.RC_CONTROL_UIH or _pf(RFCOMM_CONTROL.RC_CONTROL_UIH) == self.control:
    #         return 'UIH' 
    #     elif self.control  == RFCOMM_CONTROL.RC_CONTROL_UA or _pf(RFCOMM_CONTROL.RC_CONTROL_UA) == self.control:
    #         return 'UA'
    #     else:
    #         return None

    def parse_pkt(self):
        if not self.pkt or len(self.pkt) < 3:
            return None
        self.address = self.pkt[0]
        self.control = self.pkt[1]
        # Handle top-level RFCOMM frames
        if self.control == RFCOMM_CONTROL.RC_CONTROL_DISC or _pf(RFCOMM_CONTROL.RC_CONTROL_DISC) == self.control:
            return 'DISC'
        elif self.control == RFCOMM_CONTROL.RC_CONTROL_DM or _pf(RFCOMM_CONTROL.RC_CONTROL_DM) == self.control:
            return 'DM'
        elif self.control == RFCOMM_CONTROL.RC_CONTROL_SABM or _pf(RFCOMM_CONTROL.RC_CONTROL_SABM) == self.control:
            return 'SABM'
        elif self.control == RFCOMM_CONTROL.RC_CONTROL_UA or _pf(RFCOMM_CONTROL.RC_CONTROL_UA) == self.control:
            return 'UA'
        elif self.control == RFCOMM_CONTROL.RC_CONTROL_UIH or _pf(RFCOMM_CONTROL.RC_CONTROL_UIH) == self.control:
            # ---- UIH frame: subcommand parsing ----
            # [0]: Address, [1]: Control, [2]: Length (EA=1: 1 byte, else 2 bytes)
            len_val = self.pkt[2]
            len_bytes = 1 if (len_val & 1) else 2
            mx_offset = 3 if len_bytes == 1 else 4
            # Check if UIH payload (subcommand) exists
            if len(self.pkt) > mx_offset:
                mx_type = self.pkt[mx_offset]
                self.mx_type = mx_type
                # Mask C/R bit for all MX_TYPE comparisons
                masked_mx = mx_type_mask(mx_type)
                if masked_mx == mx_type_mask(MX_TYPE.MX_PN):
                    return 'PN'
                elif masked_mx == mx_type_mask(MX_TYPE.MX_TEST):
                    return 'TEST'
                elif masked_mx == mx_type_mask(MX_TYPE.MX_MSC):
                    return 'MSC'
                elif masked_mx == mx_type_mask(MX_TYPE.MX_FCON):
                    return 'FCON'
                elif masked_mx == mx_type_mask(MX_TYPE.MX_FCOFF):
                    return 'FCOFF'
                elif masked_mx == mx_type_mask(MX_TYPE.MX_RPN):
                    return 'RPN'
                elif masked_mx == mx_type_mask(MX_TYPE.MX_RLS):
                    return 'RLS'
                elif masked_mx == mx_type_mask(MX_TYPE.MX_NSC):
                    return 'NSC'
                else:
                    return 'UIH'  # Unknown MX_TYPE, just return 'UIH'
            else:
                return 'UIH'      # No payload found
        else:
            return None


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

"""
@timeout(3)
def inter_recv(sock): # Receive the first response
    conn_rsp = sock.recv(MTU)
    return conn_rsp, sock
"""

def process_rsps(resp_list):
    """
    Given a list of respS,
    returns a list of (resp, res) where res is not None
    (res = FRAME_PKT(resp).parse_pkt()).
    """
    results = []
    for resp in resp_list:
        frame_pkt = FRAME_PKT(resp)
        res = frame_pkt.parse_pkt()
        if res is not None:
            results.append(res)
    return results