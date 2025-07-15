"""
state.py

State constants and protocol class sets for RFCOMM message sequence logic.
These values are used across the RFCOMM state machine (see testsuite.py)
and correspond to the main states and events of RFCOMM as tested in the Bluetooth Test Suite (TS).
"""

# --- State constants for RFCOMM FSM (grouped by phase) ---

# 1. Session Setup phase
STATE_INITIATED             = 0   # Initial, before SABM(DLCI=0)
STATE_WAIT_UA_SETUP         = 1   # Waiting for UA after sending SABM(DLCI=0)

# 2. Control Management phase
STATE_ESTABLISHED_CONTROL   = 2   # Control channel established (UA received)
STATE_WAIT_PN_RESPONSE      = 3   # Waiting for PN response (after sending PN)
STATE_WAIT_TEST_RESPONSE    = 4   # Waiting for TEST response
STATE_WAIT_DISC_UA_CTRL     = 5   # Waiting for UA after sending DISC (Control)
STATE_WAIT_UA_CTRL          = 6   # Waiting for UA after sending SABM (Control phase, DLCI≠0)

# 3. Multiplexed DLC phase
STATE_DLC_OPEN              = 7   # DLCI≠0 opened (data link established)
STATE_WAIT_RPN_RESPONSE     = 8   # Waiting for RPN response
STATE_WAIT_DISC_UA_DLC      = 9   # Waiting for UA after sending DISC (DLC)

# --- Channel/role constant ---
CTRL_CHANNEL = 0  # DLCI=0 for control channel

def state2str(state):
    mapping = {
        # Session Setup phase
        STATE_INITIATED:            "Initiated",
        STATE_WAIT_UA_SETUP:        "Wait_UA (Setup)",
        # Control Management phase
        STATE_ESTABLISHED_CONTROL:  "Established_Control",
        STATE_WAIT_PN_RESPONSE:     "Wait_PN_Response",
        STATE_WAIT_TEST_RESPONSE:   "Wait_Test_Response",
        STATE_WAIT_DISC_UA_CTRL:    "Wait_DISC_UA (Ctrl)",
        STATE_WAIT_UA_CTRL:         "Wait_UA (Ctrl)",
        # Multiplexed DLC phase
        STATE_DLC_OPEN:             "DLC Open (DLCI≠0)",
        STATE_WAIT_RPN_RESPONSE:    "Wait_RPN_Response",
        STATE_WAIT_DISC_UA_DLC:     "Wait_DISC_UA (DLC)",
    }
    return mapping.get(state, f"unknown_state_{state}")

def frame2str(frame):
    """
    Return the string name for a given RFCOMM frame/command instance.
    """
    return frame.name()

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
