import random
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs, rfc_check_fcs
from layer.rfcomm.const import *

class SABM(RFCOMM):
    def __bytes__(self):
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes([calc_fcs(3, ret)])
        return ret
    
    def name():
        return 'SABM'
    
    @classmethod
    def gen(cls,channel=0, transition=False, fuzz=False, length=0, dir=0):
        ret = SABM()
        if transition:
            ret.addr = 0b00000001
            ret.addr |=  1 << 1 # C/R
            ret.addr |= 0 << 2 # Direction
            ret.addr |= channel << 3 # channel
            ret.control = RFCOMM_CONTROL.RC_CONTROL_SABM
            ret.length = 0
            return bytes(ret)
        if fuzz:
            ret.addr = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.control = RFCOMM_CONTROL.RC_CONTROL_SABM
            ret.length = gen_param(0b01111111, 1, (0b00000000, 0b01111111))
            return bytes(ret)
        ret.addr = 0b00000001
        ret.addr |= 1 << 1 # C/R
        ret.addr |= 0 << 2 # Direction
        ret.control = RFCOMM_CONTROL.RC_CONTROL_SABM
        ret.addr |= random.randint(0, 31) << 3 # channel
        ret.length = 0
        return bytes(ret)
