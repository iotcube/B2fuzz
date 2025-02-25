from layer.rfcomm.const import MX_TYPE

length = 0
class TEST:
    """
    TEST MX command generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.type: [int] command type bit

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __init__(self):
        self.type = None
        
    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        TEST type has no data field so the length field is set to 0x01

        ```
        length_field value == length*2 + 1
        ```


        Returns
        --------
        - [bytes]: TEST type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([1])
        return ret
    
    def name():
        """
        Return TEST command name

        
        Returns
        --------
        - [string] TEST frame name
        """
        return 'TEST'

    @classmethod
    def gen(cls, transition=False, fuzz=False, channel=0, dir=0):
        """
            Generate TEST command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] TEST command
        """
        # [1] initialize INVALID generator class       
        ret = TEST()

        # [2] set type bit to TEST
        ret.type = MX_TYPE.MX_TEST + (1<<1)

        # [3] return bytes
        return bytes(ret)