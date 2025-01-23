import random
from layer.rfcomm.const import MX_TYPE

length = 2
class RLS:
    def __init__(self):
        self.type: int = MX_TYPE.MX_RLS + (0<<1) # + (random.randint(0,1)<<1)
        self.line_status: int = 0
        self.DLCI = 0
    @property
    def length(self):
        return 0
    
    def __bytes__(self) -> bytes: 
        ret = b''
        ret += bytes([self.type])
        ret += bytes([5])
        ret += bytes([self.DLCI])
        ret += bytes([self.line_status])
        return ret

    @classmethod
    def gen(cls, transition=False, channel=0, dir=0):
        ret = RLS()
        ret.DLCI = channel << 3 | dir << 2 | 0b11 # EA == 1, one padding == 1
        ret.line_status = random.choice([
            0b1100,
            0b1010,
            0b1001
        ])
        return bytes(ret)