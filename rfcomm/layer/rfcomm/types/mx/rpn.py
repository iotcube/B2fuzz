# In layer/rfcomm/types/mx/rpn.py
import random
from layer.rfcomm.const import MX_TYPE

class RPN:
    """
    RPN MX command generator class.
    Generates the inner payload for an RPN command for use inside a UIH frame.
    """
    def name():
        """Return RPN command name"""
        return 'RPN'

    @classmethod
    def gen(cls, channel=0, is_response=False, port_values=None, **kwargs):
        """
        Generates the inner payload for a RPN multiplexer command.
        This consists of [type, length, dlci, (optional) port_values...].

        Parameters
        ----------
        - channel: [int] The DLCI the command refers to.
        - is_response: [bool] If True, generates a response (C/R bit = 0).
        - port_values: [bytes, optional] An 8-byte string with port settings.
                       If None, a basic RPN command without settings is generated.
        - **kwargs: Catches unused arguments for compatibility.

        Returns
        ----------
        - [bytes] The complete RPN command payload for insertion into a UIH frame.
        """
        # Determine the C/R bit (1 for Command, 0 for Response).
        cr_bit = 0 if is_response else 1
        
        # The MX_RPN constant (0x93) already has the command bit set.
        # We mask it off and then set it correctly based on is_response.
        base_type = MX_TYPE.MX_RPN & 0b11111101
        type_field = base_type | (cr_bit << 1)

        # The RPN payload's DLCI field is 6 bits: (DLCI << 2) | (dir << 1) | EA.
        # Direction bit 'D' is always 1 for commands from the initiator.
        dlci_field = (channel << 2) | (1 << 1) | 1

        # --- Backward-Compatibility and Flexibility Logic ---
        if port_values is not None:
            # NEW BEHAVIOR: Generate RPN with specific port settings.
            # The length of the data part is 1 (DLCI) + 8 (port values) = 9.
            # Length field encoding: (9 * 2) + 1 = 19 (0x13).
            length_field = 19
            payload_data = bytes([dlci_field]) + port_values
        else:
            # OLD BEHAVIOR: Generate basic RPN without port settings.
            # The length of the data part is just 1 (the DLCI).
            # Length field encoding: (1 * 2) + 1 = 3.
            length_field = 3
            payload_data = bytes([dlci_field])

        # Assemble the final command payload
        return bytes([type_field, length_field]) + payload_data