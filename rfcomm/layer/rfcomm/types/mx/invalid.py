import random

length = 0

class INVALID:
    """
    INVALID MX command generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.type: [int] command type field (random bit)

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __init__(self):
        self.type: int = (random.randint(0, 63) << 2) + (0<<1) + 1
    
    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        INVALID type has no data field so the length field is set to 0x01

        ```
        length_field value == length*2 + 1
        ```


        Returns
        --------
        - [bytes]: INVALID type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([1])
        return ret
    
    def name():
        """
        Return INVALID command name

        
        Returns
        --------
        - [string] INVALID frame name
        """
        return 'INVALID'

    @classmethod
    def gen(cls, transition=False, fuzz=False, channel=0, dir=0):
        """
            Generate INVALID command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] INVALID command
        """
        # [1] initialize INVALID generator class
        ret = INVALID()

        # [2] set type bit to INVALID
        ret.type = (random.randint(0, 63) << 2) + (0<<1) + 1
        
        # [3] return bytes
        return bytes(ret)