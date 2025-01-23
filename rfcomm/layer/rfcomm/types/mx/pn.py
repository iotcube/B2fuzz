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
        ret += bytes([self.CL << 4 + self.I])
        ret += bytes([self.P])
        ret += bytes([self.T])
        ret += (self.N).to_bytes(2, byteorder='little') # 16 bits
        ret += bytes([self.NA]) # max number of retransmission
        ret += bytes([self.K]) # err recovery mode
        return ret

    def name():
        return 'PN'

    @classmethod
    def gen(cls, transition=False, channel=0, dir=0):
        ret = PN()
        if transition:
            ret.type = MX_TYPE.MX_PN# + (random.randint(0,1)<<1)
            ret.DLCI = channel << 1
            ret.CL = 0b1111 # C1 ~ C4 = 0xf
            ret.I = 0b0000  # I1 ~ I4 = 0x0
            ret.P = 0
            ret.T = 0
            ret.N = 256
            ret.NA = 0b00000000
            ret.K = 7
            return bytes(ret)
        ret.type = MX_TYPE.MX_PN# + (random.randint(0,1)<<1)
        ret.DLCI = random.randint(0, 31)
        ret.I = 0b1000
        ret.CL = 0b0000
        ret.P = random.randint(0, 7)
        ret.T = 0
        ret.N = random.randint(0, 0xffff)
        ret.NA = 0b00000000
        ret.K = random.randint(0, 7)
        return bytes(ret)
    