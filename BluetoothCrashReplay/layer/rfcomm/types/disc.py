import random
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.const import RFCOMM_CONTROL

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
    def gen(cls, transition=False):
        ret = DISC()
        if transition:
            return b'\x03\x53\x01\xfd'
        ret.addr = 0b00000001
        ret.addr |= random.randint(0,1) << 1 # C/R
        ret.addr |= random.randint(0,1) << 2 # Direction
        ret.control = RFCOMM_CONTROL.RC_CONTROL_DISC
        ret.length = 0
        return ret
