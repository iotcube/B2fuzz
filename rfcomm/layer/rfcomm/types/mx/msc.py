import random
from layer.rfcomm.const import MX_TYPE

length = 2

class MSC:
    def __init__(self):
        self.type = MX_TYPE.MX_MSC# + (random.randint(0,1)<<1)
        self.DLCI = 0
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
        ret += bytes([5])
        ret += bytes([self.DLCI])
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
    def gen(cls, transition=False, channel=0, dir=0):
        ret = MSC()
        if transition:
            ret.DV = 1
            ret.IC = 0
            ret.RTR = 1
            ret.RTC = 1
            ret.FC = 0
            ret.EA = 1
            ret.DLCI = channel << 3 | dir << 2 | 0b11 # EA == 1, one padding == 1
            ret.reserved = 0
            ret.reserved2 = 0
            return bytes(ret)
        ret.DV = random.randint(0,1)
        ret.FC = random.randint(0,1)
        ret.IC = random.randint(0,1)
        ret.RTR = random.randint(0,1)
        ret.RTC = random.randint(0,1)
        ret.FC = random.randint(0,1)
        ret.EA = 1
        ret.reserved =0
        ret.reserved2 = 0
        return bytes(ret)