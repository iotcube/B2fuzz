import random
from layer.rfcomm.const import MX_TYPE

length = 2
class RLS:
    """
    RLS MX command generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.type: [int] command type field
    - self.DLCI: [int] DLCI
    - self.line_status: [int] line status information

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __init__(self):
        self.type: int = MX_TYPE.MX_RLS + (0<<1) # + (random.randint(0,1)<<1)
        self.line_status: int = 0
        self.DLCI = 0
    @property
    def length(self):
        return 0
    
    def __bytes__(self) -> bytes:
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        RLS type has 2 data field so the length field is set to 0x5

        ```
        length_field value == length*2 + 1
        ```
        
        Returns
        --------
        - [bytes]: RLS type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([5])
        ret += bytes([self.DLCI])
        ret += bytes([self.line_status])
        return ret

    def name():
        """
        Return RLS command name

        
        Returns
        --------
        - [string] RLS frame name
        """
        return 'RLS'

    @classmethod
    def gen(cls, transition=False, fuzz = False, channel=0, dir=0):
        """
            Generate RLS command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] RLS command
        """
        # [1] initialize RLS generator class
        ret = RLS()

        # [2] set DLCI 
        ret.DLCI = channel << 3 | dir << 2 | 0b11 # EA == 1, one padding == 1
        
        # [3] line status(defined in TS.07.10 spec) random choice 
        ret.line_status = random.choice([
            0b1100,
            0b1010,
            0b1001
        ])

        # [4] return bytes
        return bytes(ret)