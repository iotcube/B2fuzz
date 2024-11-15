import random
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs, rfc_check_fcs
from layer.rfcomm.const import RFCOMM_CONTROL

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
    def gen(cls, transition=False):
        ret = SABM()
        if transition:
            return b'\x03\x3f\x01\x1c'
        ret.addr = 0b00000001
        ret.addr |= random.randint(0,1) << 1 # C/R
        ret.addr |= random.randint(0,1) << 2 # Direction
        ret.control = RFCOMM_CONTROL.RC_CONTROL_SABM
        ret.length = 0
        return ret
