# In layer/rfcomm/types/mx/test.py

from layer.rfcomm.const import MX_TYPE
import random # Needed for fuzzing

# Helper function for random data, can be shared across modules
def gen_random_data(length):
    return bytes(random.getrandbits(8) for _ in range(length))

class TEST:
    """
    Dual-purpose TEST MX command payload generator.
    - Default: Generates predictable payloads for conformance testing.
    - Fuzzing: Generates random payloads for fuzzing.
    """
    def name():
        """Return TEST command name"""
        return 'TEST'

    @classmethod
    def gen(cls, payload=None, is_response=False, fuzz=False, **kwargs):
        """
        Generates the inner payload for a TEST multiplexer command.
        This consists of [type, length, data...].

        Parameters
        ----------
        - payload: [bytes] The specific test pattern data for conformance tests.
        - is_response: [bool] Flips the C/R bit for generating responses.
        - fuzz: [bool] If True, enables fuzzing mode.
        - **kwargs: Catches unused arguments.

        Returns
        ----------
        - [bytes] The complete TEST command payload for insertion into a UIH frame.
        """
        # --- FUZZING LOGIC ---
        if fuzz:
            # For a fuzzed TEST command, we generate a random payload.
            # The length is also randomized (e.g., up to 10 bytes).
            fuzzed_data = gen_random_data(random.randint(1, 10))
            
            # Use the standard command type, but with a random payload.
            type_field = MX_TYPE.MX_TEST
            length_field = (len(fuzzed_data) << 1) | 1
            
            return bytes([type_field, length_field]) + fuzzed_data

        # --- CONFORMANCE TESTING LOGIC (Default) ---
        
        # Set a default empty payload if none is provided for the test case.
        test_data = payload if payload is not None else b''
        
        # Determine the type field based on whether it's a command or response.
        base_type = MX_TYPE.MX_TEST
        if is_response:
            # A response flips the C/R bit from 1 (command) to 0 (response).
            # e.g., 0b...11 -> 0b...01
            type_field = base_type & ~0b00000010 
        else:
            # A command uses the type as-is.
            type_field = base_type

        # The length of the command's data payload.
        length_field = (len(test_data) << 1) | 1
        
        # Assemble the final command payload
        return bytes([type_field, length_field]) + test_data