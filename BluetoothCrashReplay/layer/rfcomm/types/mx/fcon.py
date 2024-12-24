from layer.rfcomm.const import MX_TYPE

length = 0

class FCON:
    def __init__(self):
        self.type: int = MX_TYPE.MX_FCON + (1<<1)

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
        ret = FCON()
        ret.type =  MX_TYPE.MX_FCON + (1<<1)
        return ret