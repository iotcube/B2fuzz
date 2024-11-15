import random
from layer.rfcomm.const import MX_TYPE

length = 8

class PN:
    def __init__(self):
        self.type: int = 0
        self.DLCI: int = 0
        self.I: int = 0
        self.CL: int = 0
        self.P: int = 0
        self.T: int = 0
        self.N: int = 0
        self.NA: int = 0
        self.K: int = 0

    @property
    def length(self):
        return 10
    
    def __bytes__(self):
        ret = b''
        ret += bytes([self.type])
        ret += bytes([8*2+1])
        ret += bytes([self.DLCI])
        ret += bytes([self.I << 4 + self.CL])
        ret += bytes([self.P << 1])
        ret += bytes([self.T])
        ret += (self.N).to_bytes(2, byteorder='big') # 16 bits
        ret += bytes([self.NA])
        ret += bytes([self.K << 5])
        return ret

    @classmethod
    def gen(cls):
        ret = PN()
        ret.type = MX_TYPE.MX_PN# + (random.randint(0,1)<<1)
        ret.DLCI = random.randint(0, 31)
        ret.I = 0b1000
        ret.CL = 0b0000
        ret.P = random.randint(0, 7)
        ret.T = 0
        ret.N = random.randint(0, 0xffff)
        ret.NA = 0b00000000
        ret.K = random.randint(0, 7)
        return ret
    