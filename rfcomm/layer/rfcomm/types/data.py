import random
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import *

def gen_random_data(len):
    return b''.join(random.choices([bytes([x]) for x in range(0x00, 0x100)], k=len))

class DATA(RFCOMM):
    """
    DATA frame generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.addr: [int] DLCI
    - self.control: [int] controle bit
    - self.length: [int] payload length
    - self.data: [bytes] payload data

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
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
        ret += bytes([calc_fcs(2, ret)])
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
    def gen(cls,channel=0, transition=False,fuzz=False, length=0, dir=0):
        """
            Generate DATA type frame

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - length: [int] payload length
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] DATA frame byte
        """

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
            ret.length = 0
            return bytes(ret)
        
        # [3] when fuzzing, initialize DATA frame with AFL mutator
        elif fuzz:
            ret.addr = 0b00000001
            ret.addr |= 1 << 1 # C/R
            ret.addr |= dir << 2 # Direction
            ret.addr |= channel << 3
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
            ret.data = gen_random_data(31)
            ret.length = gen_param(0b01111111, 1, (0b00000000, 0b01111111))
            return bytes(ret)


        ret.addr = 0b00000001
        ret.addr |= 1 << 1 # C/R
        ret.addr |= dir << 2 # Direction
        ret.addr |= channel << 3
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH

        ret.data = gen_random_data(length)
        ret.length = len(ret.data)#length
        
        return bytes(ret)