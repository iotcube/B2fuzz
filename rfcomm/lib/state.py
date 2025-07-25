# lib/state.py

"""
state.py

State constants and protocol class sets for RFCOMM message sequence logic.
These values are used across the RFCOMM state machine (see testsuite.py)
and correspond to the main states and events of RFCOMM as tested in the Bluetooth Test Suite (TS).
"""

from enum import Enum, auto

# Define the control channel DLCI
CTRL_CHANNEL = 0

class StateName(Enum):
    # Session-level states
    SESS_OPEN = "SESS_OPEN"
    SESS_WAIT_UA = "SESS_WAIT_UA"

    # Control channel states (DLCI=0)
    CTRL_OPEN = "CTRL_OPEN"
    CTRL_WAIT_PN = "CTRL_WAIT_PN"
    CTRL_WAIT_TEST = "CTRL_WAIT_TEST"
    CTRL_WAIT_NSC = "CTRL_WAIT_NSC"
    CTRL_WAIT_UA = "CTRL_WAIT_UA"
    CTRL_WAIT_DISC_UA = "CTRL_WAIT_DISC_UA"

    # Data channel states (DLCI > 0)
    DATA_OPEN = "DATA_OPEN"
    DATA_WAIT_MSC = "DATA_WAIT_MSC"
    DATA_WAIT_RPN = "DATA_WAIT_RPN"
    DATA_WAIT_RLS = "DATA_WAIT_RLS"
    DATA_WAIT_UA = "DATA_WAIT_UA"
    DATA_WAIT_DISC_UA = "DATA_WAIT_DISC_UA"
    DATA_CREDIT_RCVD = "DATA_CREDIT_RCVD" 

class Direction(Enum):
    SEND = auto()
    RECV = auto()
    OTHER = auto() # For events like timeouts

class EventType(Enum):
    SABM = auto()
    UA = auto()
    DM = auto()
    PN = auto()
    TEST = auto()
    DISC = auto()
    NSC = auto()
    MSC = auto()
    RLS = auto()
    RPN = auto()
    UIH = auto()
    TIMEOUT = auto()

class Event:
    """
    Represents a state machine transition event.
    """
    def __init__(self, direction, event_type, detail=None):
        self.direction = direction      # SEND, RECV, OTHER
        self.event_type = event_type    # SABM, UA, etc.
        self.detail = detail            # Optional (e.g., DLCI number)

    def __repr__(self):
        return f"{self.direction.name}:{self.event_type.name}" + (f" ({self.detail})" if self.detail is not None else "")

def state_name(enum, dlci=None):
    """
    Returns unique state name for GraphMachine.
    - enum: StateName Enum member.
    - dlci: integer or None.
    """
    # Use the enum's *value* (the string) which is now unique, not its .name
    base_name = enum.value
    if dlci is None:
        # Session-level states often don't have a DLCI.
        return base_name
    return f"{base_name}_{dlci}"



def state_label(enum, dlci=None):
    """
    Returns pretty label for visualization.
    """
    if dlci is None:
        return f"{enum.value}"
    return f"{enum.value} (DLCI {dlci})"

# --- Import RFCOMM frame and command classes ---
# Core frame types
from layer.rfcomm.types.dm import DM
from layer.rfcomm.types.disc import DISC
from layer.rfcomm.types.sabm import SABM
from layer.rfcomm.types.ua import UA
from layer.rfcomm.types.uih import UIH
from layer.rfcomm.types.uih import DATA

# Command/extension messages (in UIH or special frames)
from layer.rfcomm.types.mx.fcoff import FCOFF
from layer.rfcomm.types.mx.fcon import FCON
from layer.rfcomm.types.mx.invalid import INVALID
from layer.rfcomm.types.mx.msc import MSC
from layer.rfcomm.types.mx.nsc import NSC
from layer.rfcomm.types.mx.pn import PN
from layer.rfcomm.types.mx.rls import RLS
from layer.rfcomm.types.mx.rpn import RPN
from layer.rfcomm.types.mx.test import TEST

# --- Frame and Command class sets ---
# "Frames" are top-level RFCOMM packets (A=Address, C=Control, etc)
RFCOMM_FRAMES = [
    SABM, UA, DM, DISC, UIH, DATA
]

# "Commands" are multiplexed control messages, usually in UIH frame payloads
RFCOMM_COMMANDS = [
    PN, RPN, TEST, MSC, RLS, NSC, FCON, FCOFF, INVALID
]

# --- (Optionally: frame/command lookup by name, for dynamic fuzzing, etc) ---
FRAME_NAME_MAP = {cls.__name__: cls for cls in RFCOMM_FRAMES}
COMMAND_NAME_MAP = {cls.__name__: cls for cls in RFCOMM_COMMANDS}

# --- Hidden state path utility (for advanced path tracking) ---
hidden_state_path = []
"""
[List of tuple] For storing "hidden" or new state paths.

- hidden_state_path[i][0]: transition function for source state
- hidden_state_path[i][1]: [bytes] frame for transition to new state
- See also: modules.construct_sm.expand_sm, modules.mutation_new.new_state_fuzzing
"""
