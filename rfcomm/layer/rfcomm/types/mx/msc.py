import random
from layer.rfcomm.const import *

length = 2

class MSC:
    """
    MSC MX command generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.type: [int] command type field
    - self.DLCI: [int] DLCI 
    - self.EA: [int] EA bit
    - self.FC: [int] FC bit
    - self.RTC: [int] RTC bit
    - self.reserved: [int] reserved bit
    - self.reserved2: [int] reserved bit
    - self.IC: [int] IC bit
    - self.DV: [int] DV

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __init__(self):
        self.type = MX_TYPE.MX_MSC# + (random.randint(0,1)<<1)
        self.DLCI = 0
        self.EA: int = 1
        self.FC: int = 0
        self.RTC: int = 0
        self.RTR: int = 0 
        self.reserved: int = 0
        self.reserved2: int = 0
        self.IC: int = 0
        self.DV: int = 0

    @property
    def length(self):
        return 0
    
    def __bytes__(self) -> bytes:
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        MSC type has 2 data field so the length field is set to 0x05

        ```
        length_field value == length*2 + 1
        ```

        Attributes like DV, IC,,, is **bit** type data.
        

        Returns
        --------
        - [bytes]: MSC type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([5])
        ret += bytes([self.DLCI])
        ret += bytes([
            (self.DV << 7) +
            (self.IC << 6) +
            (self.reserved << 5) +
            (self.reserved2 << 4) + 
            (self.RTR << 3) +
            (self.RTC << 2) +
            (self.FC << 1) +
            (self.EA << 0)
        ])
        return ret
    
    def name():
        """
        Return MSC command name

        
        Returns
        --------
        - [string] MSC frame name
        """
        return 'MSC'

    @classmethod
    def gen(cls, transition=False, fuzz= False, channel=0, dir=0):
        """
            Generate MSC command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] MSC command
        """

        # [1] initialize MSC generator class       
        ret = MSC()

        # [2] when transition, initialize MSC command with information for transition  
        if transition:
            ret.DV = 1
            ret.IC = 0
            ret.RTR = 1
            ret.RTC = 1
            ret.FC = 0
            ret.EA = 1
            ret.DLCI = channel << 3 | dir << 2 | 0b11 # EA == 1, one padding == 1
            ret.reserved = 0
            ret.reserved2 = 0
            return bytes(ret)
        
        # [3] when fuzzing, initialize MSC command with AFL mutator
        elif fuzz:
            ret.DV = random.randint(0,1)
            ret.FC = random.randint(0,1)
            ret.IC = random.randint(0,1)
            ret.RTR = random.randint(0,1)
            ret.RTC = random.randint(0,1)
            ret.FC = random.randint(0,1)
            ret.EA = 1
            ret.reserved =0
            ret.reserved2 = 0
            ret.DLCI = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            return bytes(ret)

        ret.DV = random.randint(0,1)
        ret.FC = random.randint(0,1)
        ret.IC = random.randint(0,1)
        ret.RTR = random.randint(0,1)
        ret.RTC = random.randint(0,1)
        ret.FC = random.randint(0,1)
        ret.EA = 1
        ret.reserved =0
        ret.reserved2 = 0
        return bytes(ret)