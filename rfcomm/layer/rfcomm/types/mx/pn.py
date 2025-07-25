# In layer/rfcomm/types/mx/pn.py

import random
from layer.rfcomm.const import *

class PN:
    """
    Dual-purpose PN MX command generator class.
    - Default: Generates a specific, non-compliant payload required by the target device.
    - Fuzzing: Generates random payloads for fuzzing.
    """
    def __init__(self):
        self.type: int = 0
        self.DLCI: int = 0
        self.I: int = 0
        self.CL: int = 0
        self.P: int = 0
        self.T: int = 0
        self.N: int = 0
        self.NA: int = 0
        self.K: int = 0

    def __bytes__(self):
        """
        Serializes the PN object into the correct byte format for the command payload.
        """
        length_field = 17 # 8 data bytes * 2 + 1
        ret = b''
        ret += bytes([self.type])
        ret += bytes([length_field])
        ret += bytes([self.DLCI])
        ret += bytes([(self.CL << 4) | self.I])
        ret += bytes([self.P])
        ret += bytes([self.T])
        ret += (self.N).to_bytes(2, byteorder='little')
        ret += bytes([self.NA])
        ret += bytes([self.K])
        return ret

    def name():
        return 'PN'

    @classmethod
    def gen(cls, channel=0, is_response=False, fuzz=False, **kwargs):
        """
        Generates the inner payload for a PN multiplexer command.
        """
        ret = PN()

        # --- FUZZING LOGIC (Preserved from your original file) ---
        if fuzz:
            # This logic remains the same.
            ret.type = MX_TYPE.MX_PN
            # Assuming gen_param is a function available for fuzzing.
            ret.DLCI = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.CL = random.randint(0, 15)
            ret.I = random.randint(0, 15)
            ret.P = gen_param(0, 1, (0, 255))
            ret.T = gen_param(0, 1, (0, 255))
            ret.N = gen_param(256, 2, (0, 65535))
            ret.NA = gen_param(0, 1, (0, 255))
            ret.K = gen_param(0, 1, (0, 255))
            return bytes(ret)

        # --- CONFORMANCE TESTING LOGIC (Reverted to match Old Code) ---
        
        # FIX #1: Use the exact type from the working "Old Code".
        # The device expects a PN Response (0x83) as a command.
        ret.type = MX_TYPE.MX_PN 
        
        # FIX #2: Use the exact DLCI calculation from the working "Old Code".
        # This is non-compliant but is what the target device expects.
        ret.DLCI = channel << 1
        
        # The rest of the parameters are from the working "Old Code".
        ret.CL = 0b1111      # Supported command types
        ret.I = 0b0000       # Reserved, must be 0
        ret.P = 0            # Priority
        ret.T = 0            # Acknowledgment timer
        ret.N = 256          # Max frame size
        ret.NA = 0           # Max retransmissions
        ret.K = 7            # Initial credits
        
        return bytes(ret)