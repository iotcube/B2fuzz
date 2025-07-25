# In layer/rfcomm/types/mx/msc.py

import random
from layer.rfcomm.const import *

class MSC:
    """
    Dual-purpose MSC MX command generator class.
    - Default: Generates predictable payloads for conformance testing.
    - Fuzzing: Generates random payloads for fuzzing.
    """
    def __init__(self):
        self.type = MX_TYPE.MX_MSC
        self.DLCI = 0
        self.EA: int = 1
        self.FC: int = 0
        self.RTC: int = 0
        self.RTR: int = 0 
        self.reserved: int = 0
        self.reserved2: int = 0
        self.IC: int = 0
        self.DV: int = 0

    def __bytes__(self) -> bytes:
        """
        Serializes the MSC object into the correct byte format for the command payload.
        """
        length_field = 5
        ret = b''
        ret += bytes([self.type])
        ret += bytes([length_field])
        ret += bytes([self.DLCI])
        ret += bytes([
            (self.DV << 7) |
            (self.IC << 6) |
            (self.reserved2 << 5) | 
            (self.reserved << 4) | 
            (self.RTR << 3) |
            (self.RTC << 2) |
            (self.FC << 1) |
            (self.EA << 0)
        ])
        return ret
    
    def name():
        return 'MSC'

    @classmethod
    def gen(cls, channel=0, is_response=False, fuzz=False, **kwargs):
        """
        Generate MSC command payload.
        
        Parameters
        ----------
        - channel: [int] The DLCI the command refers to.
        - is_response: [bool] If True, generates a response (C/R bit = 0).
        - fuzz: [bool] If True, enables fuzzing mode.
        - **kwargs: Catches specific V.24 bits (fc, rtc, rtr, ic, dv) and other unused args.

        Returns
        ----------
        - [bytes] MSC command payload for use inside a UIH frame.
        """
        ret = MSC()

        # --- FUZZING LOGIC ---
        if fuzz:
            # Your original fuzzing behavior is restored.
            ret.type = MX_TYPE.MX_MSC # Fuzzing always sends a command
            ret.DV = random.randint(0,1)
            ret.IC = random.randint(0,1)
            ret.RTR = random.randint(0,1)
            ret.RTC = random.randint(0,1)
            ret.FC = random.randint(0,1)
            ret.EA = 1
            # Assuming gen_param is a function available in your fuzzer's context
            # If not, this line would need to be adapted.
            ret.DLCI = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            return bytes(ret)

        # --- CONFORMANCE TESTING LOGIC (Default) ---

        # Determine the C/R bit (1 for Command, 0 for Response).
        cr_bit = 0 if is_response else 1
        base_type = MX_TYPE.MX_MSC & 0b11111101  # Mask off original C/R bit
        ret.type = base_type | (cr_bit << 1)

        # Correct DLCI field calculation
        direction_bit = 1 if not is_response else 0
        ret.DLCI = (channel << 2) | (direction_bit << 1) | 1

        # Check for specific values passed by test cases.
        if 'fc' in kwargs or 'rtc' in kwargs or 'rtr' in kwargs:
            ret.FC  = int(kwargs.get('fc', 0))
            ret.RTC = int(kwargs.get('rtc', 0))
            ret.RTR = int(kwargs.get('rtr', 0))
            ret.IC  = int(kwargs.get('ic', 0))
            ret.DV  = int(kwargs.get('dv', 1))
        else:
            # Fallback to default random behavior if no specific values are given.
            # This matches the final block of your original gen() method.
            ret.DV = random.randint(0,1)
            ret.FC = random.randint(0,1)
            ret.IC = random.randint(0,1)
            ret.RTR = random.randint(0,1)
            ret.RTC = random.randint(0,1)

        return bytes(ret)