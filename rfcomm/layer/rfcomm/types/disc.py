# In layer/rfcomm/types/disc.py

import random
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.const import *

class DISC(RFCOMM):
    """
    Dual-purpose DISC frame generator class.
    - Default: Generates predictable frames for conformance testing.
    - Fuzzing: Generates random/mutated frames for fuzzing.
    """
    def __bytes__(self):
        """
        Serializes the DISC object into the correct byte format.
        DISC frames have no data payload.
        """
        # The header consists of Address, Control, and a 1-byte Length field.
        header = bytes([self.addr, self.control, (self.length << 1) | 1])
        
        # FCS for DISC is calculated over the 3 header bytes.
        fcs = calc_fcs(3, header)
        
        return header + bytes([fcs])
  
    def name():
        """
        Return DISC frame name
        """
        return 'DISC'

    @classmethod
    def gen(cls, channel=0, fuzz=False, **kwargs):
        """
        Generates a complete DISC frame.

        Parameters
        ----------
        - channel: [int] The specific DLCI to send the frame to for conformance tests.
        - fuzz: [bool] If True, enables fuzzing mode.
        - **kwargs: Catches unused arguments like 'transition'.

        Returns
        ----------
        - [bytes] A complete DISC frame.
        """
        ret = DISC()
        
        # --- FUZZING LOGIC ---
        if fuzz:
            # Your original fuzzing logic is restored here.
            # It mutates the address and length fields.
            # Assuming gen_param is available in the fuzzing context.
            ret.addr = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
            # A valid DISC length is 0, but fuzzing can test other values.
            ret.length = gen_param(0, 1, (0, 127))
            return bytes(ret)

        # --- CONFORMANCE TESTING LOGIC (Default) ---
        # This is your original 'transition=True' block, which is the correct
        # way to generate a standard DISC command for a specific channel.
        
        # Address field: DLCI, Direction, and C/R bit.
        # A command from the initiator has C/R = 1.
        cr_bit = 1
        direction_bit = 0 # Initiator to responder
        
        ret.addr = 0b00000001 # EA bit
        ret.addr |= cr_bit << 1
        ret.addr |= direction_bit << 2
        ret.addr |= (channel & 0x1F) << 3 # Use the specified channel
            
        ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
        
        # A valid DISC frame has no data payload, so length is always 0.
        ret.length = 0
        
        return bytes(ret)