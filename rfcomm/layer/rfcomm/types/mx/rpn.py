import random
from layer.rfcomm.const import *

class RPN:
    """
    RPN MX command generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.type: [int] command type field
    - self.DLCI: [int] DLCI
    - self.EA: [int] EA field
    - seld.BR: [int] BR field
    - self.DB: [int] DB bit
    - self.SB: [int] SB bit
    - self.P: [int] P bit
    - self.PT: [int] PT bit
    - self.R: [int] R field
    - self.R2: [int] R2 field
    - self.FC: [int] FC field
    - self.XON: [int] XON field
    - self.XOFF: [int]XOFF field
    - self.PM_bit_rate: [int] PM_bit_rate bit
    - self.PM_data_bits: [int] PM_data_bits
    - self.PM_stop_bits: [int] PM_stop_bits 
    - self.PM_parity: [int] PM_parity
    - self.PM_parity_type: [int] PM_parity_type
    - self.PM_xon_char: [int] PM_xon_char bit
    - self.PM_xoff_char: [int] PM_xoff_char bit
    - self.PM_input_xon_xoff: [int] PM_input_xon_xoff bit
    - self.PM_output_xon_xoff: [int] PM_output_xon_xoff bit  
    - self.PM_input_RTR: [int] PM_input_RTR bit
    - self.PM_output_RTR: [int] PM_output_RTR bit
    - self.PM_input_RTC: [int] PM_input_RTC bit
    - self.PM_output_RTC: [int] PM_output_RTC bit


    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __init__(self):
        self.type: int = MX_TYPE.MX_RPN# + (random.randint(0,1)<<1)
        self.DLCI: int = 0
        self.EA: int = 1
        self.BR: int = 0
        self.DB: int = 0
        self.SB: int = 0
        self.P: int = 0
        self.PT: int = 0
        self.R: int = 0
        self.R2: int = 0
        self.FC: int = 0
        self.XON: int = 0
        self.XOFF: int = 0
        self.PM_bit_rate: int = 0
        self.PM_data_bits: int = 0
        self.PM_stop_bits: int = 0
        self.PM_parity: int = 0
        self.PM_parity_type: int = 0
        self.PM_xon_char: int = 0
        self.PM_xoff_char: int = 0
        self.PM_input_xon_xoff: int = 0
        self.PM_output_xon_xoff: int = 0
        self.PM_input_RTR: int = 0
        self.PM_output_RTR: int = 0
        self.PM_input_RTC: int = 0
        self.PM_output_RTC: int = 0

    @property
    def length(self):
        return 8
    
    def __bytes__(self) -> bytes:
        """
        When byte() method is called, this method is runed\n

        Note
        -----
        RPN type has 8 data field so the length field is set to 2*8+1

        ```
        length_field value == length*2 + 1
        ```
        
        Returns
        --------
        - [bytes]: RPN type command 
        """
        ret = b''
        ret += bytes([self.type])
        ret += bytes([17])
        ret += bytes([
            self.DLCI
        ])
        ret += bytes([
            self.BR
        ])
        ret += bytes([
            self.DB + (self.SB << 2) + (self.P << 3) + (self.PT << 4)
        ])
        ret += bytes([
            self.FC
        ])
        ret += bytes([self.XON])
        ret += bytes([self.XOFF])
        ret += bytes([
            self.PM_bit_rate + (self.PM_data_bits << 1) + (self.PM_stop_bits << 2) + (self.PM_parity << 3) + (self.PM_parity_type << 4) + \
            (self.PM_xon_char << 5) + (self.PM_xoff_char << 6)
        ])
        ret += bytes([
            self.PM_input_xon_xoff + (self.PM_output_xon_xoff << 1) + (self.PM_input_RTR << 2) + (self.PM_output_RTR << 3) + (self.PM_input_RTC << 4) + (self.PM_output_RTC << 5)
        ])
        return ret
    
    def name():
        """
        Return RPN command name

        
        Returns
        --------
        - [string] RPN frame name
        """
        return 'RPN'

    @classmethod
    def gen(cls, transition=False, fuzz=False, channel=0, dir=0):
        """
            Generate RPN command

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - dir: [int] direction bit


            Returns
            ----------
            - [bytes] RPN command
        """
        # [1] initialize RPN generator class
        ret = RPN()

        # [2] initialize RPN command with AFL mutator
        ret.type = MX_TYPE.MX_RPN
        ret.DLCI = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
        ret.EA = 1
        ret.BR = random.randint(0, 8) # RFCOMM_RPN_BR_230400 = 8
        ret.DB = random.randint(0, 4)
        ret.SB = random.randint(0, 1)
        ret.P = random.randint(0, 1)
        ret.PT = 0
        ret.FC = gen_param(0x00, 1, (0b00000000, 0b11111111))
        ret.XON = gen_param(0x11, 1, (0b00000000, 0b11111111))
        ret.XOFF = gen_param(0x13, 1, (0b00000000, 0b11111111))
        ret.PM_bit_rate = random.randint(0, 1)
        ret.PM_data_bits = random.randint(0, 1)
        ret.PM_stop_bits = random.randint(0, 1)
        ret.PM_parity = random.randint(0, 1)
        ret.PM_parity_type = random.randint(0, 1)
        ret.PM_xon_char = random.randint(0, 1)
        ret.PM_xoff_char = random.randint(0, 1)
        ret.PM_input_xon_xoff = random.randint(0, 1)
        ret.PM_output_xon_xoff = random.randint(0, 1)
        ret.PM_input_RTR = random.randint(0, 1)
        ret.PM_output_RTR = random.randint(0, 1)
        ret.PM_input_RTC = random.randint(0, 1)
        ret.PM_output_RTC = random.randint(0, 1)

        # [3] return bytes
        return bytes(ret)
