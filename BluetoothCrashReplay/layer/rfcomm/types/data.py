import random
from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import RFCOMM_CONTROL

def gen_random_data(len):
    return b''.join(random.choices([bytes([x]) for x in range(0x00, 0x100)], k=len))

class DATA(RFCOMM):
    def __bytes__(self):
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += self.data
        ret += bytes([calc_fcs(2, ret)])
        return ret
    
    def name():
        return 'UIH'

    @classmethod
    def gen(cls):
        ret = DATA()
        ret.addr = 0b00000001
        ret.addr |= random.randint(0,1) << 1 # C/R
        ret.addr |= random.randint(0,1) << 2 # Direction
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
        ret.length = random.randint(0, 127)
        ret.data = gen_random_data(ret.length)
        return ret