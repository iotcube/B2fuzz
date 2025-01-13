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
    def gen(cls,channel=0, transition=False, length=0):
        ret = DATA()
        if transition:
            ret.addr = 0b00000001
            ret.addr |= 1 << 1 # C/R
            ret.addr |= 0 << 2 # Direction
            ret.addr |= channel << 3
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH | 0b00010000 # P/F flag
            ret.data = b"\x21"
            ret.length = 0
            return bytes(ret)
        
        ret.addr = 0b00000001
        ret.addr |= 1 << 1 # C/R
        ret.addr |= 0 << 2 # Direction
        ret.addr |= channel << 3
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH

        ret.data = b"\r\nAT+BSRF=671\r\n"#gen_random_data(ret.length)
        ret.length = len(ret.data)#length
        
        return ret