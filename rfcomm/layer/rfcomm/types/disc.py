import random
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.const import *

class DISC(RFCOMM):
    """
    DISC frame generator class\n

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
        - [bytes]: DISC type frame with fcs byte 
        """
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes([calc_fcs(3, ret)])
        return ret
  
    def name():
        """
        Return DISC frame name

        
        Returns
        --------
        - [string] DISC frame name

        """
        return 'DISC'

    @classmethod
    def gen(cls,channel=0, transition=False,fuzz=False, length=0, dir=0):
        """
            Generate DISC type frame

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - length: [int] payload length
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] DISC frame byte
        """

        # [1] initialize DISC generator class
        ret = DISC()

        # [2] when transition, initialize DISC frame with information for transition
        if transition:
            ret.addr = 0b00000001
            ret.addr |= 1 << 1          # C/R bit set to 1 (Command)
            ret.addr |= 0 << 2          # Direction bit = 0
            ret.addr |= channel << 3    # Set DLCI bits
            ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
            ret.length = 0
            return bytes(ret)
        
        # [3] when fuzzing, initialize DISC frame with AFL mutator
        elif fuzz:
            ret.addr = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
            ret.length = gen_param(0b01111111, 1, (0b00000000, 0b01111111))
            return bytes(ret)

        ret.addr = 0b00000001
        ret.addr |= 0 << 1              # C/R bit set to 0 (Response)
        ret.addr |= dir << 2            # Direction bit set from parameter
        ret.addr |= channel << 3        # Set DLCI bits
        ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
        ret.length = 0
        return bytes(ret)
