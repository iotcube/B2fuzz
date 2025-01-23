import random
from layer.rfcomm.const import MX_TYPE

length = 1
class NSC:
    def __init__(self):
        self.type = MX_TYPE.MX_NSC
        self.cmd_type = 0
    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        ret = b''
        ret += bytes(self.type)
        ret += bytes([3])
        ret += bytes(self.cmd_type)
        return ret
    
    @classmethod
    def gen(cls):
        ret = NSC()
        ret.cmd_type = random.randint(0, 255)
        return bytes(ret)