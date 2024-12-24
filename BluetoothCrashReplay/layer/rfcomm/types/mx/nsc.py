import random
from layer.rfcomm.const import MX_TYPE

length = 1
class NSC:
    def __init__(self):
        ...
    @property
    def length(self):
        return 0
    
    def __bytes__(self):
        ret = b''
        return ret
    
    @classmethod
    def gen(cls):
        ret = NSC()
        return ret