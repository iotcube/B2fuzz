# In layer/rfcomm/types/data.py

import random
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import *

def gen_random_data(length):
    return bytes(random.getrandbits(8) for _ in range(length))

class DATA(RFCOMM):
    """
    Dual-purpose DATA payload generator class for UIH frames.
    - Default: Generates predictable payloads for conformance testing.
    - Fuzzing: Generates random data payloads for fuzzing.
    """
    def __bytes__(self):
        """
        This method is kept for backward compatibility in case the DATA class
        was ever instantiated and serialized directly, but the primary logic
        is now in the static gen() method.
        """
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += self.data
        fcs_header = bytes([self.addr, self.control])
        ret += bytes([calc_fcs(2, fcs_header)])
        return ret
    
    def name():
        """
        Return DATA type name
        """
        return 'DATA'

    @classmethod
    def gen(cls, payload=None, credit=0, fuzz=False, **kwargs):
        """
        Generates a data payload for use within a UIH frame.
        This method *only* returns the payload bytes.

        Parameters
        ----------
        - payload: [bytes, optional] The specific data to be sent for conformance tests.
        - credit: [int, optional] The number of credits to prepend for flow control.
        - fuzz: [bool] If True, enables fuzzing mode.
        - **kwargs: Catches unused arguments like 'channel', 'transition'.

        Returns
        ----------
        - [bytes] The data payload, possibly prepended with a credit byte.
        """
        # --- FUZZING LOGIC ---
        if fuzz:
            # For a fuzzed data payload, we generate random data of a random length.
            # Credits can also be randomized.
            fuzzed_data = gen_random_data(random.randint(1, 31))
            fuzzed_credit = random.randint(0, 15)
            
            if fuzzed_credit > 0:
                return bytes([fuzzed_credit]) + fuzzed_data
            else:
                return fuzzed_data

        # --- CONFORMANCE TESTING LOGIC (Default) ---
        
        # Determine the data payload. If none is provided, use an empty byte string.
        data_to_send = payload if payload is not None else b''
        
        # Prepend the credit byte if credits are being sent.
        if credit > 0:
            return bytes([credit]) + data_to_send
        else:
            return data_to_send