import random
from layer.rfcomm.const import MX_TYPE

class RPN:
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
        ret = b''
        ret += bytes([self.type])
        ret += bytes([17])
        ret += bytes([
            self.EA +
            (0<<1) +
            (self.DLCI << 2)
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
    
    @classmethod
    def gen(cls):
        ret = RPN()
        ret.type = MX_TYPE.MX_RPN
        ret.DLCI = random.randint(0, 31)
        ret.EA = 1
        ret.BR = random.randint(0, 8) # RFCOMM_RPN_BR_230400 = 8
        ret.DB = 3 #random.randint(0, 4)
        ret.SB = 0 #random.randint(0, 1)
        ret.P = 0 #random.randint(0, 1)
        ret.PT = 0
        ret.FC = 0x00
        ret.XON = 0x11
        ret.XOFF = 0x13
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
        return ret
