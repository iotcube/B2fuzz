import random
from layer.rfcomm.const import MX_TYPE

length = 2

class MSC:
    def __init__(self):
        self.type = MX_TYPE.MX_MSC# + (random.randint(0,1)<<1)
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
        ret = b''
        ret += bytes([self.type])
        ret += bytes([17])
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
    
    @classmethod
    def gen(cls):
        ret = MSC()
        ret.DV = random.randint(0,1)
        ret.FC = random.randint(0,1)
        ret.IC = random.randint(0,1)
        ret.RTR = random.randint(0,1)
        ret.RTC = random.randint(0,1)
        ret.FC = random.randint(0,1)
        ret.EA = 1
        ret.reserved = random.randint(0,1)
        ret.reserved2 = random.randint(0,1)
        return ret