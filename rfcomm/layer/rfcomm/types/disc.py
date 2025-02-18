import random
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.const import *

class DISC(RFCOMM):
    def __bytes__(self):
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes([calc_fcs(3, ret)])
        return ret
  
    def name():
        return 'DISC'

    @classmethod
    def gen(cls,channel=0, transition=False,fuzz=False, length=0, dir=0):
        ret = DISC()
        if transition:
            ret.addr = 0b00000001
            ret.addr |= 1 << 1 # C/R
            ret.addr |= 0 << 2 # Direction\
            ret.addr |= channel << 3
            ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
            ret.length = 0
            return bytes(ret)
        elif fuzz:
            ret.addr = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
            ret.length = gen_param(0b01111111, 1, (0b00000000, 0b01111111))
            return bytes(ret)

        ret.addr = 0b00000001
        ret.addr |= 0 << 1 # C/R
        ret.addr |= dir << 2 # Direction
        ret.addr |= channel << 3
        ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
        ret.length = 0
        return bytes(ret)
