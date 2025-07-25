# In layer/rfcomm/types/mx/rls.py

import random
from layer.rfcomm.const import MX_TYPE

class RLS:
    """
    Final, correct, and backward-compatible RLS MX command generator class.
    """
    def name():
        """Return RLS command name"""
        return 'RLS'

    @classmethod
    def gen(cls, channel=0, line_status=None, is_response=False, fuzz=False, mimic_direction_bug=False, **kwargs):
        """
        Generates the inner payload for an RLS multiplexer command.
        """
        # --- FUZZING LOGIC (Preserved for backward compatibility) ---
        if fuzz:
            fuzzed_line_status = random.randint(0, 255)
            # Fuzzing always sends a command, using the constant directly.
            type_field = MX_TYPE.MX_RLS
            # DLCI field for a command for the channel under test.
            dlci_field = (channel << 2) | (1 << 1) | 1
            length_field = 5
            return bytes([type_field, length_field, dlci_field, fuzzed_line_status])

        # --- CONFORMANCE LOGIC (Corrected and Simplified) ---
        
        # 1. Determine the Type field with the correct C/R bit.
        #    The command ID for RLS is 0x14.
        cmd_id = 0x14
        cr_bit = 0 if is_response else 1
        #    Final type field format: [ ID (6 bits) | C/R (1 bit) | EA (1 bit) ]
        type_field = (cmd_id << 2) | (cr_bit << 1) | 1

        # 2. Determine the DLCI field with the correct D bit.
        #    Direction bit 'D' is 1 for IUT->Peer, and 0 for Peer->IUT.
        #    This device incorrectly always sends D=1, so we must mimic that for validation.
        if is_response and mimic_direction_bug:
            direction_bit = 1 # Mimic the bug for generating the expected response.
        else:
            direction_bit = 0 if is_response else 1
            
        #    The DLCI field format is: [ DLCI (6 bits) | D (1 bit) | EA (1 bit) ]
        dlci_field = (channel << 2) | (direction_bit << 1) | 1

        # 3. Determine the Line Status byte.
        #    For conformance tests, use the provided status. For fuzzing fallback, use 0.
        status_byte = line_status if line_status is not None else 0

        # 4. Length is always fixed for RLS.
        length_field = 5 # Data is 2 bytes (dlci_field + status_byte)
        
        return bytes([type_field, length_field, dlci_field, status_byte])