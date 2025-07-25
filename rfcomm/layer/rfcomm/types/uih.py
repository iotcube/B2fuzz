# In layer/rfcomm/types/uih.py

import random

from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import *
from layer.rfcomm.types.mx.fcoff import FCOFF
from layer.rfcomm.types.mx.fcon import FCON
from layer.rfcomm.types.mx.invalid import INVALID
from layer.rfcomm.types.mx.msc import MSC
from layer.rfcomm.types.mx.nsc import NSC
from layer.rfcomm.types.mx.pn import PN
from layer.rfcomm.types.mx.rls import RLS
from layer.rfcomm.types.mx.rpn import RPN
from layer.rfcomm.types.mx.test import TEST
from layer.rfcomm.types.data import DATA
MX_TYPE = [
    FCOFF, FCON, INVALID, MSC, NSC, PN, RLS, RPN, TEST, DATA
]

class UIH(RFCOMM):
    """
    Dual-purpose UIH frame generator class.
    - Default: Generates predictable frames for conformance testing.
    - Fuzzing: Generates random/mutated frames for fuzzing.
    """
    def __bytes__(self):
        """
        Serializes the UIH object.
        Uses the 2-byte FCS calculation that is compatible with your target device.
        """
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes(self.data)
        fcs_header = bytes([self.addr, self.control])
        ret += bytes([calc_fcs(2, fcs_header)])
        return ret
    
    def name():
        return 'UIH'
    
    @classmethod
    def gen(cls, channel=0, channel_to_ctrl=0, transition=False, fuzz=False, mx_type=None, dir=0, **kwargs):
        """
        Generates a complete UIH frame.
        """
        ret = UIH()
        
        # --- FUZZING LOGIC ---
        if fuzz:
            # Your original fuzzing logic is restored here.
            # Assuming gen_param is available in the fuzzing context.
            ret.addr = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
            # The inner command is also generated in fuzz mode.
            ret.data = random.choice(MX_TYPE).gen(fuzz=True)
            ret.length = gen_param(0, 1, (0, 127)) # Length can be fuzzed
            return bytes(ret)

        # --- CONFORMANCE TESTING LOGIC (Default) ---
        
        # Build Address Field for a command from the initiator (C/R = 1).
        cr_bit = 1
        ret.addr = 0b00000001 # EA bit
        ret.addr |= cr_bit << 1
        ret.addr |= (dir & 0x1) << 2
        ret.addr |= (channel & 0x1F) << 3

        # Set Control Field. Your target device expects UIH without P/F bit.
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
        
        # If a specific multiplexer command is requested, generate its payload.
        if mx_type:
            payload_gen_args = {
                'transition': transition,
                'fuzz': False, # Ensure sub-generators are not in fuzz mode
                'channel': channel_to_ctrl,
                'dir': dir,
                **kwargs
            }
            ret.data = mx_type.gen(**payload_gen_args)
        else:
            # This handles cases where a UIH is sent with only user data (not a command)
            # The payload is taken directly from the 'payload' kwarg.
            ret.data = kwargs.get('payload', b'')

        ret.length = len(ret.data)
        
        return bytes(ret)