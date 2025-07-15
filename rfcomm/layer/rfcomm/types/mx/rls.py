import random
from layer.rfcomm.const import MX_TYPE

class RLS:
    def name():
        return 'RLS'

    @classmethod
    def gen(cls, channel=0, line_status=None, is_response=False, mimic_direction_bug=False, **kwargs):
        """
        Generates RLS payload. Includes a flag to mimic a common bug where the
        responder does not flip the direction bit in the DLCI field.
        """
        # Type Field Logic
        base_type = MX_TYPE.MX_RLS
        type_field = base_type & ~0b00000010 if is_response else base_type

        # DLCI Field Logic (With Bug-Mimicking Fix)
        if mimic_direction_bug:
            # Force the direction bit to 1 (command direction) for validation
            direction_bit = 1
        else:
            # Normal behavior: 0 for response, 1 for command
            direction_bit = 0 if is_response else 1
            
        dlci_field = (channel << 2) | (direction_bit << 1) | 1

        # Remainder of the logic
        status_byte = line_status if line_status is not None else random.choice([0b1100, 0b1010, 0b1001])
        length_field = 5
        
        return bytes([type_field, length_field, dlci_field, status_byte])