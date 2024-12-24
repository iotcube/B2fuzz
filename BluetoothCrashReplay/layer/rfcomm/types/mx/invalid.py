import random

length = 0

class INVALID:
    def __init__(self):
        self.type: int = (random.randint(0, 63) << 2) + (0<<1) + 1
    
    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        ret = b''
        ret += bytes([self.type])
        ret += bytes([1])
        return ret
    
    @classmethod
    def gen(cls):
        ret = INVALID()
        ret.type = (random.randint(0, 63) << 2) + (0<<1) + 1
        return ret