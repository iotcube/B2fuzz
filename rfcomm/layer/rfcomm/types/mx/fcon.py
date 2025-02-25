from layer.rfcomm.const import MX_TYPE

length = 0

class FCON:
    """
    FCON MX command generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.type: [int] command type field

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __init__(self):
        self.type: int = MX_TYPE.MX_FCON + (1<<1)

    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        FCON type has no data field so the length field is set to 0x01

        ```
        length_field value == length*2 + 1
        ```


        Returns
        --------
        - [bytes]: FCON type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([1])
        return ret
    
    def name():
        """
        Return FCON command name

        
        Returns
        --------
        - [string] FCON frame name
        """
        return 'FCON'

    @classmethod
    def gen(cls, transition=False, fuzz=False, channel=0, dir=0):
        """
            Generate FCON command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] FCON command
        """
        # [1] initialize FCON generator class
        ret = FCON()
        
        # [2] set type bit to FCON
        ret.type =  MX_TYPE.MX_FCON | (1<<1)

        # [3] return bytes
        return bytes(ret)