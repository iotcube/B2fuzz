import random
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import *

class DM(RFCOMM):
    """
    DM frame generator class\n

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
        - [bytes]: DM type frame with fcs byte 
        """
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes([calc_fcs(3, ret)])
        return ret
    
    def name():
        """
        Return DM frame name

        
        Returns
        --------
        - [string] DM frame name
        """
        return 'DM'
    
    @classmethod
    def gen(cls,channel=0, transition=False,fuzz=False, length=0, dir=0):
        """
            Generate DM type frame

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - length: [int] payload length
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] DM frame byte
        """

        # [1] initialize DM generator class
        ret = DM()

        # [2] when fuzzing, initialize DM frame with AFL mutator
        if fuzz:
            ret.addr = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UA
            ret.length = gen_param(0b01111111, 1, (0b00000000, 0b01111111))
            return bytes(ret)
        
        # [3] when transition, initialize DM frame with information for transition
        ret.addr = 0b00000001
        ret.addr |= 0 << 1 # C/R
        ret.addr |= dir << 2 # Direction
        ret.addr |= channel << 3
        ret.control = RFCOMM_CONTROL.RC_CONTROL_DM
        ret.length = 0
        return bytes(ret)
