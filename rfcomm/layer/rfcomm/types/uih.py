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
    UIH frame generator class.
    """
    def __bytes__(self):
        """
        Kept for compatibility. The main logic is in gen().
        """
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes(self.data)
        # Use the 2-byte FCS calculation that is compatible with the target device.
        fcs_header = bytes([self.addr, self.control])
        ret += bytes([calc_fcs(2, fcs_header)])
        return ret
    
    def name():
        return 'UIH'
    
    @classmethod
    def gen(cls, channel=0, channel_to_ctrl=0, transition=False, fuzz=False, mx_type=None, dir=0, **kwargs):
        """
        Generate UIH type frame.
        """
        ret = UIH()
        
        # --- FUZZING PATH (unchanged) ---
        if fuzz:
            # Your fuzzing logic seems to set its own address, so we leave it alone.
            ret.addr = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
            ret.data = random.choice(MX_TYPE).gen(fuzz=True)
            ret.length = gen_param(0b01111111, 1, (0b00000000, 0b01111111))
            return bytes(ret)

        # --- STANDARD PATH (Corrected) ---
        
        # ** THE FIX: Always use the bit-shifting logic to build the address. **
        # This ensures the C/R bit is set correctly for commands (C/R=1).
        # A command from the initiator has C/R = 1.
        # Direction bit is 0 for initiator->responder frames.
        cr_bit = 1 # We are the initiator, sending commands.
        ret.addr = 0b00000001 # EA bit
        ret.addr |= cr_bit << 1
        ret.addr |= (dir & 0x1) << 2
        ret.addr |= (channel & 0x1F) << 3

        # Set control field. Your working code does not use the P/F bit for UIH.
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH

        # Generate payload from the specified mx_type
        if mx_type:
            payload_gen_args = {
                'transition': transition, 'fuzz': fuzz, 'channel': channel_to_ctrl, 'dir': dir, **kwargs
            }
            ret.data = mx_type.gen(**payload_gen_args)
        else:
            ret.data = b'' # Default to empty payload
        ret.length = len(ret.data)
        
        # The __bytes__ method will be called when we return, which correctly
        # uses the 2-byte FCS that your device expects.
        return bytes(ret)