# In layer/rfcomm/types/mx/nsc.py

import random
from layer.rfcomm.const import MX_TYPE

class NSC:
    """
    Dual-purpose NSC MX command generator class.
    - Default: Generates predictable payloads for validating test case responses.
    - Fuzzing: Generates random payloads for fuzzing.
    """
    def __init__(self):
        self.type = MX_TYPE.MX_NSC
        self.cmd_type = 0 # The command type that was not supported
    
    def __bytes__(self):
        """
        Serializes the NSC object into the correct byte format for the command payload.
        """
        # The data part of an NSC is 1 byte: [Unsupported Command Type]
        # Length field encoding: (1 * 2) + 1 = 3.
        length_field = 3
        
        ret = b''
        ret += bytes([self.type])
        ret += bytes([length_field])
        ret += bytes([self.cmd_type])
        return ret
    
    def name():
        """
        Return NSC command name
        """
        return 'NSC'

    @classmethod
    def gen(cls, unsupported_cmd_type=None, fuzz=False, **kwargs):
        """
        Generates the inner payload for an NSC multiplexer command (response).

        Parameters
        ----------
        - unsupported_cmd_type: [int, optional] The specific command type to embed in the NSC response.
                                If None, falls back to fuzzing/random behavior.
        - fuzz: [bool] If True, enables fuzzing mode (generates a random unsupported_cmd_type).
        - **kwargs: Catches unused arguments like 'channel' and 'transition'.

        Returns
        ----------
        - [bytes] The complete NSC command payload for insertion into a UIH frame.
        """
        ret = NSC()

        # The NSC is always a response, so its C/R bit in the type field should be 0.
        # We assume the MX_TYPE.MX_NSC constant is correctly defined for a response.
        ret.type = MX_TYPE.MX_NSC

        # --- FUZZING LOGIC ---
        if fuzz:
            # For fuzzing, we generate a random byte for the unsupported command field.
            ret.cmd_type = random.randint(0, 255)
            return bytes(ret)

        # --- CONFORMANCE TESTING LOGIC (Default) ---
        if unsupported_cmd_type is not None:
            # Use the specific command type provided by the test case for validation.
            ret.cmd_type = unsupported_cmd_type
        else:
            # Fallback to the original random behavior if no specific type is given.
            ret.cmd_type = random.randint(0, 255)
            
        return bytes(ret)