import random
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import RFCOMM_CONTROL

class UA(RFCOMM):
    def __bytes__(self):
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes([calc_fcs(3, ret)])
        return ret
    
    def name():
        return 'UA'

    @classmethod
    def gen(cls,channel=0, transition=False, length=0, dir=0):
        ret = UA()
        ret.addr = 0b00000001
        ret.addr |= 0 << 1 # C/R
        ret.addr |= dir << 2 # Direction
        ret.addr |= channel << 3
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UA
        ret.length = 0
        return bytes(ret)
