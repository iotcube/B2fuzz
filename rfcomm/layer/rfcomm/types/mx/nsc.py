import random
from layer.rfcomm.const import MX_TYPE

length = 1
class NSC:
    """
    NSC MX command generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.type: [int] command type field of NSC
    - self.cmd_type: [int] command type field(random bit)

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __init__(self):
        self.type = MX_TYPE.MX_NSC
        self.cmd_type = 0
    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        MSC type has 1 data field so the length field is set to 0x03

        ```
        length_field value == length*2 + 1
        ```
        
        Returns
        --------
        - [bytes]: NSC type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([3])
        ret += bytes([self.cmd_type])
        return ret
    
    def name():
        """
        Return NSC command name

        
        Returns
        --------
        - [string] NSC frame name
        """
        return 'NSC'

    @classmethod
    def gen(cls, transition=False, fuzz=False, channel=0, dir=0):
        """
            Generate NSC command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] NSC command
        """

        # [1] initialize NSC generator class
        ret = NSC()

        # [2] set type bit to NSC
        ret.cmd_type = random.randint(0, 255)

        # [3] return bytes
        return bytes(ret)