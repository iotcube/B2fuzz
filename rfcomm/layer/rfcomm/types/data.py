import random
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import *

def gen_random_data(len):
    return b''.join(random.choices([bytes([x]) for x in range(0x00, 0x100)], k=len))

class DATA(RFCOMM):
    """
    DATA frame generator class. Can generate a full frame or just a payload
    depending on the provided arguments.
    """
    def __bytes__(self):
        """
        When byte() method is called, this method is runed\n

        Returns
        --------
        - [bytes]: DATA type frame with fcs byte 
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
        Return DATA frame name

        
        Returns
        --------
        - [string]: DATA frame name 
        """
        return 'DATA'

    @classmethod
    def gen(cls, channel=0, transition=False, fuzz=False, length=0, dir=0, payload=None, credit=0, **kwargs):
        """
            Generate a DATA frame or payload.

            If 'payload' or 'credit' are provided, this method returns *only the payload bytes*
            for use inside another frame (like UIH).

            Otherwise, it generates a *complete, standalone UIH frame* with random data,
            maintaining backward compatibility.

            Parameters
            ----------
            - channel, transition, fuzz, length, dir: Original arguments for full frame generation.
            - payload: [bytes] If provided, triggers payload-only generation.
            - credit: [int] If > 0, triggers payload-only generation and prepends a credit byte.
            - **kwargs: Catches unused arguments.

            Returns
            ----------
            - [bytes] A full RFCOMM frame OR just a data payload.
        """
        # --- NEW LOGIC: Check for new arguments to decide the behavior ---
        if payload is not None or credit > 0:
            # BEHAVIOR 1: Generate payload only (for tc_BV_21_C)
            data_to_send = payload if payload is not None else b''
            if credit > 0:
                return bytes([credit]) + data_to_send
            else:
                return data_to_send

        # --- ORIGINAL LOGIC: For full frame generation (backward compatibility) ---
        # If the new arguments are not present, execute the original code.
        
        # [1] initialize DATA generator class
        ret = DATA()

        # [2] when transition, initialize DATA frame with information for transition
        if transition:
            ret.addr = 0b00000001
            ret.addr |= 1 << 1 # C/R
            ret.addr |= dir << 2 # Direction
            ret.addr |= channel << 3
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH | 0b00010000 # P/F flag
            ret.data = b"\x21"
            ret.length = 1 # The length of the data is 1
            return bytes(ret)
        
        # [3] when fuzzing, initialize DATA frame with AFL mutator
        elif fuzz:
            ret.addr = 0b00000001
            ret.addr |= 1 << 1 # C/R
            ret.addr |= dir << 2 # Direction
            ret.addr |= channel << 3
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
            ret.data = gen_random_data(31)
            # Assuming gen_param is defined for fuzzing
            ret.length = gen_param(0b01111111, 1, (0b00000000, 0b01111111))
            return bytes(ret)

        # [4] Default original behavior
        ret.addr = 0b00000001
        ret.addr |= 1 << 1 # C/R
        ret.addr |= dir << 2 # Direction
        ret.addr |= channel << 3
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH

        ret.data = gen_random_data(length)
        ret.length = len(ret.data)
        
        return bytes(ret)