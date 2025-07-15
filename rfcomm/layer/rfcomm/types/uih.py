import random

from layer.rfcomm.types.base import RFCOMM
from layer.rfcomm.util import calc_fcs
from layer.rfcomm.const import *
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
    TEST,
    # Adding DATA allows it to be used as a multiplexer command type
    DATA
]

class UIH(RFCOMM):
    """
    UIH frame generator class\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
    - self.addr: [int] DLCI
    - self.control: [int] controle bit
    - self.length: [int] payload length
    - self.data: [bytes] payload data

    Methods
    ----------
     - `.__bytes__()`
     - `.name()`
     - `.gen()`
    """
    def __bytes__(self):
        """
        When byte() method is called, this method is runed\n

        Returns
        --------
        - [bytes]: UIH type frame with fcs byte 
        """
        ret = bytes([self.addr])
        ret += bytes([self.control])
        ret += bytes([(self.length << 1) + 1])
        ret += bytes(self.data)
        # Original FCS calculation
        fcs_header = bytes([self.addr, self.control])
        ret += bytes([calc_fcs(2, fcs_header)])
        return ret
    
    def name():
        """
        Return UIH frame name

        
        Returns
        --------
        - [string] UIH frame name
        """
        return 'UIH'
    
    @classmethod
    def gen(cls,channel=0, channel_to_ctrl=0, transition=False, fuzz=False, mx_type=None, dir=0, **kwargs):
        """
            Generate UIH type frame

            Parameters
            ----------
            - channel: [int] DLCI to send frame
            - channel_to_ctrl: [int] DLCI to control with MX command
            - transition: [bool] transition condition (used state transition)
            - fuzz: [bool] fuzz condition (used when fuzzing)
            - mx_type: MX command type defined in `layer.rfcomm.types.mx`
            - dir: [int] direction bit
            - **kwargs: Additional arguments for payload generators (e.g., `payload`, `credit`)


            Returns
            ----------
            - [bytes] UIH frame byte
        """

        # [1] initialize UIH generator class
        ret = UIH()

        # [2] when transition, initialize UIH frame with information for transition
        if transition:
            ret.addr = 0b00000001
            ret.addr |= 1 << 1 # C/R
            ret.addr |= 0 << 2 # Direction
            ret.addr |= channel << 3
            # THIS IS THE KEY: We use the original, unmodified control field.
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
            if mx_type is None:
                ret.data = random.choice(MX_TYPE).gen()
            else:
                # We pass kwargs here to allow special arguments if needed by the payload generator.
                ret.data = mx_type.gen(transition=transition, channel=channel_to_ctrl,fuzz=fuzz, dir=dir, **kwargs)
            ret.length = len(ret.data)
            return bytes(ret)
        
        # [3] when fuzzing, initialize UIH frame with AFL mutator
        elif fuzz:
            ret.addr = gen_param(0b00000011, 1, (0b00000011, 0b11111011))
            ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
            ret.data = ret.data = random.choice(MX_TYPE).gen(fuzz=True)
            ret.length = gen_param(0b01111111, 1, (0b00000000, 0b01111111))
            return bytes(ret)
        
        # [4] Default case (non-transition, non-fuzz)
        ret.addr = 0b00000001
        ret.addr |= 1 << 1 # C/R
        ret.addr |= 0 << 2 # Direction
        ret.control = RFCOMM_CONTROL.RC_CONTROL_UIH
        ret.addr |= channel << 3
        if mx_type is None:
            ret.data = random.choice(MX_TYPE).gen()
        else:
            # We also pass kwargs here. This is the path taken by tc_BV_21_C.
            ret.data = mx_type.gen(channel=channel_to_ctrl, fuzz=fuzz, **kwargs)
        ret.length = len(ret.data)
        return bytes(ret)