import random
from layer.rfcomm.const import *

length = 8

class PN:
    """
    PN MX command generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.type: [int] command type field
    - self.DLCI: [int] DLCI
    - self.I: [int] I field
    - self.CL: [int] CL field
    - self.P: [int] P field
    - self.T: [int] T field
    - self.N: [int] N field
    - self.NA: [int] NA field
    - self.K: [int] K field

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __init__(self):
        self.type: int = 0
        self.DLCI: int = 0
        self.I: int = 0
        self.CL: int = 0
        self.P: int = 0
        self.T: int = 0
        self.N: int = 0
        self.NA: int = 0
        self.K: int = 0

    @property
    def length(self):
        return 10
    
    def __bytes__(self):
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        PN type has 8 data field so the length field is set to 2*8+1

        ```
        length_field value == length*2 + 1
        ```
        
        Returns
        --------
        - [bytes]: PN type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([8*2+1])
        ret += bytes([self.DLCI])
        ret += bytes([self.CL << 4 | self.I])
        ret += bytes([self.P])
        ret += bytes([self.T])
        ret += (self.N).to_bytes(2, byteorder='little') # 16 bits
        ret += bytes([self.NA]) # max number of retransmission
        ret += bytes([self.K]) # err recovery mode
        return ret

    def name():
        """
        Return PN command name

        
        Returns
        --------
        - [string] PN frame name
        """
        return 'PN'

    @classmethod
    def gen(cls, transition=False, fuzz=False, channel=0, dir=0):
        """
            Generate PN command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] PN command
        """
        # [1] initialize PN generator class
        ret = PN()

        # [2] when transition, initialize PN command with information for transition  
        if transition:
            ret.type = MX_TYPE.MX_PN# + (random.randint(0,1)<<1)
            ret.DLCI = channel << 1
            ret.CL = 0b1111 # C1 ~ C4 = 0xf
            ret.I = 0b0000  # I1 ~ I4 = 0x0
            ret.P = 0
            ret.T = 0
            ret.N = 256
            ret.NA = 0b00000000
            ret.K = 7
            return bytes(ret)
        
        # [3] when fuzzing, initialize PN command with AFL mutator
        elif fuzz:
            ret.type = MX_TYPE.MX_PN# + (random.randint(0,1)<<1)
            ret.DLCI = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.CL = random.randint(0, 15)
            ret.I = random.randint(0, 15)
            ret.P = gen_param(0b00000000, 1, (0b00000000, 0b11111111))
            ret.T = gen_param(0b00000000, 1, (0b00000000, 0b11111111))
            ret.N = gen_param(256, 2, (0x0000, 0xffff))
            ret.NA = gen_param(0b00000000, 1, (0b00000000, 0b11111111))
            ret.K = gen_param(0b00000000, 1, (0b00000000, 0b11111111))
            return bytes(ret)
        

        
        ret.type = MX_TYPE.MX_PN# + (random.randint(0,1)<<1)
        ret.DLCI = random.randint(0, 31)
        ret.I = 0b1000
        ret.CL = 0b0000
        ret.P = random.randint(0, 7)
        ret.T = 0
        ret.N = random.randint(0, 0xffff)
        ret.NA = 0b00000000
        ret.K = random.randint(0, 7)
        return bytes(ret)
    