# In layer/rfcomm/types/mx/fcoff.py

from layer.rfcomm.const import MX_TYPE
import random # Kept for consistency, though not used

class FCOFF:
    """
    Dual-purpose FCOFF MX command generator class.
    Generates a standard FCOFF command payload.
    """
    def name():
        """
        Return FCOFF command name
        """
        return 'FCOFF'

    @classmethod
    def gen(cls, is_response=False, fuzz=False, **kwargs):
        """
        Generates the inner payload for an FCOFF multiplexer command.
        This consists of [type, length].

        Parameters
        ----------
        - is_response: [bool] If True, generates a response (C/R bit = 0).
        - fuzz: [bool] This flag is present for consistency but doesn't change behavior.
        - **kwargs: Catches unused arguments like 'channel' and 'transition'.

        Returns
        ----------
        - [bytes] The complete FCOFF command payload for insertion into a UIH frame.
        """
        # The FCOFF command has no data payload, so its data length is 0.
        # The length field is always (0 * 2) + 1 = 1.
        length_field = 1
        
        # Determine the C/R bit (1 for Command, 0 for Response).
        cr_bit = 0 if is_response else 1
        
        # The MX_FCOFF constant (0x63) has the command bit set. We'll ensure it's correct.
        base_type = MX_TYPE.MX_FCOFF & 0b11111101  # Mask off original C/R bit
        type_field = base_type | (cr_bit << 1)
        
        # Assemble the final command payload
        return bytes([type_field, length_field])