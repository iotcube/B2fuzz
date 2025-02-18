from layer.rfcomm.const import MX_TYPE

length = 0
class TEST:
    def __init__(self):
        self.type = None
        
    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        ret = b''
        ret += bytes([self.type])
        ret += bytes([1])
        return ret
    
    def name():
        return 'TEST'

    @classmethod
    def gen(cls, transition=False, fuzz=False, channel=0, dir=0):
        ret = TEST()
        ret.type = MX_TYPE.MX_TEST + (1<<1)
        return bytes(ret)