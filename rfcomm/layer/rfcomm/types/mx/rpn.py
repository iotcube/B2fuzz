# In layer/rfcomm/types/mx/rpn.py
import random
from layer.rfcomm.const import MX_TYPE

# Helper function for random data
def gen_random_data(length):
    return bytes(random.getrandbits(8) for _ in range(length))

class RPN:
    """
    Dual-purpose RPN MX command generator class.
    - Default: Generates predictable payloads for conformance testing.
    - Fuzzing: Generates random payloads for fuzzing.
    """
    def name():
        """Return RPN command name"""
        return 'RPN'

    @classmethod
    def gen(cls, channel=0, is_response=False, port_values=None, fuzz=False, **kwargs):
        """
        Generates the inner payload for a RPN multiplexer command.
        This consists of [type, length, dlci, (optional) port_values...].

        Parameters
        ----------
        - channel: [int] The DLCI the command refers to.
        - is_response: [bool] If True, generates a response (C/R bit = 0).
        - port_values: [bytes, optional] An 8-byte string with port settings for conformance tests.
        - fuzz: [bool] If True, enables fuzzing mode.
        - **kwargs: Catches unused arguments for compatibility.

        Returns
        ----------
        - [bytes] The complete RPN command payload for insertion into a UIH frame.
        """
        # --- FUZZING LOGIC ---
        if fuzz:
            # For a fuzzed RPN command, we'll randomly decide whether to include
            # the 8-byte port values or not.
            include_port_values = random.choice([True, False])
            
            # The type is always a command in fuzzing mode
            type_field = MX_TYPE.MX_RPN
            
            # The DLCI field refers to the channel under test
            dlci_field = (channel << 2) | (1 << 1) | 1

            if include_port_values:
                # Generate a full RPN command with a random 8-byte payload
                fuzzed_port_values = gen_random_data(8)
                length_field = 19 # (1 + 8 data bytes) * 2 + 1
                payload_data = bytes([dlci_field]) + fuzzed_port_values
            else:
                # Generate a basic RPN command
                length_field = 3 # (1 data byte) * 2 + 1
                payload_data = bytes([dlci_field])
            
            return bytes([type_field, length_field]) + payload_data

        # --- CONFORMANCE TESTING LOGIC (Default) ---

        # Determine the C/R bit (1 for Command, 0 for Response).
        cr_bit = 0 if is_response else 1
        base_type = MX_TYPE.MX_RPN & 0b11111101
        type_field = base_type | (cr_bit << 1)

        # The RPN payload's DLCI field
        dlci_field = (channel << 2) | (1 << 1) | 1

        # Check if specific port values were provided for the test case
        if port_values is not None:
            # Generate RPN with the specific 8-byte port settings.
            length_field = 19 # Data length is 1 (DLCI) + 8 (port values) = 9
            payload_data = bytes([dlci_field]) + port_values
        else:
            # Generate basic 1-octet RPN (for querying settings).
            length_field = 3 # Data length is 1 (DLCI)
            payload_data = bytes([dlci_field])

        # Assemble the final command payload
        return bytes([type_field, length_field]) + payload_data