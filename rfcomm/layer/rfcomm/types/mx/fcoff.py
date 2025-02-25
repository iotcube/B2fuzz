from layer.rfcomm.const import MX_TYPE

length = 0

class FCOFF:
    """
    FCOFF MX command generator class\n

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
        self.type: int = MX_TYPE.MX_FCOFF + (1<<1)

    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        FCOFF type has no data field so the length field is set to 0x01

        ```
        length_field value == length*2 + 1
        ```


        Returns
        --------
        - [bytes]: FCOFF type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([1])
        return ret
    
    def name():
        """
        Return FCOFF command name

        
        Returns
        --------
        - [string] FCOFF frame name
        """
        return 'FCOFF'

    @classmethod
    def gen(cls, transition=False, fuzz=False, channel=0, dir=0):
        """
            Generate FCOFF command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] FCOFF command
        """

        # [1] initialize FCOFF generator class
        ret = FCOFF()

        # [2] set type bit to FCOFF
        ret.type =  MX_TYPE.MX_FCOFF | (1<<1)

        # [3] return bytes
        return bytes(ret)