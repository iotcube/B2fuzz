import random

from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import RFCOMM_CONTROL
from layer.rfcomm.types.mx.fcoff import FCOFF
from layer.rfcomm.types.mx.fcon import FCON
from layer.rfcomm.types.mx.invalid import INVALID
from layer.rfcomm.types.mx.msc import MSC
from layer.rfcomm.types.mx.nsc import NSC
from layer.rfcomm.types.mx.pn import PN
from layer.rfcomm.types.mx.rls import RLS
from layer.rfcomm.types.mx.rpn import RPN
from layer.rfcomm.types.mx.test import TEST
from layer.rfcomm.types.data import DATA
MX_TYPE = [
    FCOFF,
    FCON,
    INVALID,
    MSC,
    NSC,
    PN,
    RLS,
    RPN,
    TEST
]

class UIH(RFCOMM):
    def __bytes__(self):
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes(self.data)
        ret += bytes([calc_fcs(2, ret)])
        return ret
    
    def name():
        return 'UIH'
    
    @classmethod
    def gen(cls, mx_type=None):
        ret = UIH()
        #ret.addr = 0b00000101 + (random.randint(0, 30) << 3)
        ret.addr = 0b00000001
        ret.addr |= random.randint(0,1) << 1 # C/R
        ret.addr |= random.randint(0,1) << 2 # Direction
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
        if mx_type is None:
            ret.data = random.choice(MX_TYPE).gen()
        else:
            ret.data = mx_type.gen()
        ret.length = ret.data.length
        return ret
