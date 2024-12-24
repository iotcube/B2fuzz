from layer.rfcomm.const import MX_TYPE

length = 0

class FCOFF:
    def __init__(self):
        self.type: int = MX_TYPE.MX_FCOFF + (1<<1)

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
        ret = FCOFF()
        ret.type =  MX_TYPE.MX_FCOFF + (1<<1)
        return ret