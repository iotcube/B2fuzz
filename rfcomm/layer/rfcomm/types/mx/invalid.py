# In layer/rfcomm/types/mx/invalid.py

import random
from layer.rfcomm.const import MX_TYPE

# Helper function for random data
def gen_random_data(length):
    return bytes(random.getrandbits(8) for _ in range(length))

# A set of all valid, known command type IDs for quick lookup.
VALID_CMD_IDS = {
    (MX_TYPE.MX_PN >> 2), (MX_TYPE.MX_TEST >> 2), (MX_TYPE.MX_MSC >> 2),
    (MX_TYPE.MX_FCON >> 2), (MX_TYPE.MX_FCOFF >> 2), (MX_TYPE.MX_RPN >> 2),
    (MX_TYPE.MX_RLS >> 2), (MX_TYPE.MX_NSC >> 2),
}

class INVALID:
    """
    Dual-purpose INVALID MX command generator class.
    - Default: Generates a specific, structured invalid command for BV-25-C.
    - Fuzzing: Generates a randomized invalid command.
    """
    def __init__(self):
        self.type: int = 0
        self.payload: bytes = b''
    
    def __bytes__(self):
        """
        Serializes the INVALID object into the correct byte format for the command payload.
        """
        data_length = len(self.payload)
        length_field = (data_length << 1) | 1
        
        ret = b''
        ret += bytes([self.type])
        ret += bytes([length_field])
        ret += self.payload
        return ret
    
    def name():
        """
        Return INVALID command name
        """
        return 'INVALID'

    @classmethod
    def gen(cls, fuzz=False, **kwargs):
        """
        Generates the inner payload for an INVALID multiplexer command.

        Parameters
        ----------
        - fuzz: [bool] If True, generates a randomized invalid command.
                       If False (default), generates the specific command for BV-25-C.
        - **kwargs: Catches unused arguments.

        Returns
        ----------
        - [bytes] The complete INVALID command payload for insertion into a UIH frame.
        """
        ret = INVALID()

        # --- FUZZING LOGIC ---
        if fuzz:
            # Generate a random command type ID that is guaranteed to be invalid.
            random_cmd_id = random.randint(0, 63)
            while random_cmd_id in VALID_CMD_IDS:
                random_cmd_id = random.randint(0, 63)
            
            # Construct the full type field as a command (C/R = 1).
            ret.type = (random_cmd_id << 2) | (1 << 1) | 1
            
            # A fuzzed invalid command might have a random payload.
            ret.payload = gen_random_data(random.randint(0, 16))
            
            return bytes(ret)

        # --- CONFORMANCE TESTING LOGIC (Default for BV-25-C) ---
        
        # 1. Use a specific, non-supported command type (e.g., 0xN3).
        #    Let's use N=1, so the command ID is 0x04.
        #    Full type field = (0x04 << 2) | (1 << 1) | 1 = 0x13.
        ret.type = 0x13
        
        # 2. The spec requires a data payload of 8 random bytes for this test.
        ret.payload = gen_random_data(8)
        
        return bytes(ret)