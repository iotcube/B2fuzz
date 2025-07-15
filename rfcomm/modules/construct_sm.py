"""
construct_sm.py

Constructs a RFCOMM channel-specific state machine for a target Bluetooth device,
according to the Bluetooth SIG RFCOMM Test Suite (TS) procedures.

Uses state constants, frame/command definitions from state.py,
and message sequence logic from testsuite.py.
Supports optional graph visualization of the resulting state machine.
"""

from lib.btpkt import FRAME_PKT, inter_recv
from lib.state import *  # 상태 상수 및 프레임/커맨드
from collections import defaultdict
from termcolor import colored
import time
import copy
import os, sys
from transitions.extensions import GraphMachine

VISUALIZE = 1
"""
Flag value to print out base, adaptive state machine.
0 -> disable
1 -> enable

If enabled, `base_sm.png`, `expanded_sm.png` are generated.
"""

tmp_pkt = None
"""
Temporary variable to store the last sent frame for debugging.
"""

class Visualize:
    """
    Wrapper class for `GraphMachine` to visualize the state machine.
    """
    def __init__(self) -> None:
        self.m = GraphMachine(model=self, graph_engine="pygraphviz", 
            states=[state2str(STATE_INITIATED)],
            initial=state2str(STATE_INITIATED)
        )

    def add_state(self, state):
        """Add a state node to the graph."""
        self.m.add_state(state)

    def add_tr(self, src, dst, frame):
        """Add a transition edge to the graph."""
        self.m.add_transition(frame, src, dst)

class SMTraverseError(Exception):
    """
    Error for state transition violation.

    This error is raised when a base state transition does not proceed as expected.
    """
    def __init__(self, msg):
        self.msg = msg
    
    def __str__(self):
        return self.msg

vis = Visualize()
"""
Global Visualize instance for graph construction.
"""

hidden_state_path = []
"""
[List of tuple] - stores newly discovered (hidden) state transitions.
Format:
    - [0]: function for transition (see testsuite.py)
    - [1]: bytes of the frame that caused the transition
"""

def delete_paired_dev(target_addr):
    """
    Utility: Removes a Bluetooth device from the paired list (not used in main logic).
    """
    os.system(f"bluetoothctl disconnect {target_addr}")
    os.system(f"bluetoothctl remove {target_addr}")

def print_sm(sm):
    """
    Converts state and frame objects in the state machine to strings for pretty-printing.

    Args:
        sm (dict): state machine

    Returns:
        dict: printable state machine structure
    """
    ret = {}
    for ch in sm:
        per_ch_sm = {}
        for state in sm[ch]:
            per_ch_sm[state2str(state)] = [f.name() for f in sm[ch][state]]
        ret[f"channel{ch}"] = per_ch_sm
    return ret

def construct_sm(target_addr, dlci, VISUALIZE=False, vis=None):
    """
    Dynamically probe the peer's RFCOMM baseline state machine by running test suites (tc_*) in Control and DLC phases.
    Each tc_ function attempts a defined transition, and the observed/confirmed state is recorded in state_machine.
    Args:
        target_addr (str): MAC address of the target device
        dlci (int): Target DLCI
        VISUALIZE (bool): Whether to render visualization
        vis: Visualization engine (if any)
    Returns:
        dict: Inferred state machine (per channel, per state, with allowed frames)
    """
    from collections import defaultdict
    from modules.testsuite import (
        tc_BV_01_C, tc_BV_05_C, tc_BV_04_C, tc_BV_07_C,
        tc_BV_11_C, tc_BV_14_C, tc_BV_17_C, tc_BV_21_C, tc_BV_25_C
    )

    state_machine = defaultdict(dict)
    sock = None
    try:
        # 1. Session open (BV-01-C)
        print(colored("[TC] BV-01-C: Session open", "cyan"), end=" ")
        sock = tc_BV_01_C(target_addr)
        if not sock:
            print(colored("[Fail]", "red"))
            return None
        print(colored("[OK]", "green"))
        state_machine[CTRL_CHANNEL][STATE_ESTABLISHED_CONTROL] = [PN, TEST, DISC]
        if VISUALIZE and vis:
            vis.add_state(state2str(STATE_ESTABLISHED_CONTROL))
        time.sleep(0.5)

        # 2. Control phase testcases (loop)
        print(colored("[TC] BV-11-C: TEST command", "cyan"), end=" ")
        ok = tc_BV_11_C(sock)
        print(colored("[OK]", "green") if ok else colored("[Fail]", "red"))
        time.sleep(0.5)

        print(colored("[TC] BV-25-C: NSC (unsupported command)", "cyan"), end=" ")
        ok = tc_BV_25_C(sock)
        print(colored("[OK]", "green") if ok else colored("[Fail]", "red"))
        time.sleep(0.5)
        # ... (더 많은 컨트롤 채널 기반 TC가 있으면 여기에 확장) ...

        # 3. DLCI open (BV-05-C)
        print(colored(f"[TC] BV-05-C: Open DLCI={dlci}", "cyan"), end=" ")
        ok = tc_BV_05_C(sock, dlci)
        if not ok:
            print(colored("[Fail]", "red"))
            sock.close()
            return None
        print(colored("[OK]", "green"))
        state_machine[dlci][STATE_DLC_OPEN] = [RPN, TEST, DATA, MSC, DISC]
        if VISUALIZE and vis:
            vis.add_state(state2str(STATE_DLC_OPEN))
            vis.add_tr(state2str(STATE_ESTABLISHED_CONTROL), state2str(STATE_DLC_OPEN), "SABM")

        # 4. DLC phase testcases (loop, all performed on open DLCI)
        time.sleep(0.5)
        print(colored(f"[TC] BV-14-C: RLS command (DLCI={dlci})", "cyan"), end=" ")
        ok = tc_BV_14_C(sock, dlci)
        print(colored("[OK]", "green") if ok else colored("[Fail]", "red"))

        time.sleep(0.5)
        print(colored(f"[TC] BV-17-C: RPN command (DLCI={dlci})", "cyan"), end=" ")
        ok = tc_BV_17_C(sock, dlci)
        print(colored("[OK]", "green") if ok else colored("[Fail]", "red"))

        time.sleep(0.5)
        print(colored(f"[TC] BV-21-C: Credit-based flow (DLCI={dlci})", "cyan"), end=" ")
        ok = tc_BV_21_C(sock, dlci)
        print(colored("[OK]", "green") if ok else colored("[Fail]", "red"))

        # ... (더 많은 DLCI 기반 TC가 있으면 여기에 확장) ...

        # 5. DLCI close
        print(colored(f"[TC] BV-07-C: Close DLCI={dlci}", "cyan"), end=" ")
        ok = tc_BV_07_C(sock, dlci)
        print(colored("[OK]", "green") if ok else colored("[Fail]", "red"))

        # 6. Session shutdown
        print(colored("[TC] BV-04-C: Shutdown", "cyan"), end=" ")
        ok = tc_BV_04_C(sock)
        if ok:
            print(colored("[OK]", "green"))
            state_machine[CTRL_CHANNEL][STATE_INITIATED] = [SABM]
            if VISUALIZE and vis:
                vis.add_state(state2str(STATE_INITIATED))
                vis.add_tr(state2str(STATE_DLC_OPEN), state2str(STATE_INITIATED), "DISC")
        else:
            print(colored("[Fail]", "red"))

    except Exception as e:
        print(f"[-] construct_sm: {e}")
        import traceback
        traceback.print_exc()
        print(state_machine)
        if sock:
            sock.close()
        return None
    if sock:
        sock.close()

    print(colored("\n[Result] Inferred State Machine:", "cyan"))
    from pprint import pprint
    pprint(dict(state_machine))
    return state_machine


# def construct_sm(target_addr, dlci):
#     """
#     Constructs a DLCI-specific RFCOMM state machine for the given target,
#     following the Bluetooth SIG RFCOMM Test Suite (TS).

#     Args:
#         target_addr (str): MAC address of the target device
#         dlci (int): target profile DLCI (channel number > 0)

#     Returns:
#         dict: state machine structure
#     """

#     # Initialize state machine as a nested dict: {channel: {state: [allowed_frames]}}
#     state_machine = defaultdict(dict)
#     try:
#         # --- 1. L2CAP session only (initial state) ---
#         print(colored("(1/8) L2CAP connection established"), end="", flush=True)
#         sock = l2cap_establish(target_addr)
#         if sock:
#             print(colored(" [Success]", "green"))
#             state_machine[CTRL_CHANNEL][STATE_L2CAP_ESTABLISHED] = [SABM]
#             if VISUALIZE:
#                 vis.add_state(state2str(STATE_L2CAP_ESTABLISHED))
#             sock.close()
            
#         time.sleep(3)

#         # --- 2. Control session (DLCI=0) ---
#         print(colored("(2/8) Control channel session (DLCI=0)"), end="", flush=True)
#         sock = ctrl_session(target_addr)
#         if sock:
#             print(colored(" [Success]", "green"))
#             state_machine[CTRL_CHANNEL][STATE_CTRL_SESSION] = [DISC, PN]
#             if VISUALIZE:
#                 vis.add_state(state2str(STATE_CTRL_SESSION))
#                 vis.add_tr(state2str(STATE_L2CAP_ESTABLISHED), state2str(STATE_CTRL_SESSION), "SABM")
#             sock.close()
#         else:
#             print(colored(" [Fail]", "red"))
#         time.sleep(3)

#         # --- 3. DLCI=n parameter negotiation (PN) ---
#         print(colored(f"(3/8) DLCI={dlci} parameter negotiation (PN exchange)"), end="", flush=True)
#         sock = negotiate_dlc_params(target_addr, dlci)
#         if sock:
#             print(colored(" [Success]", "green"))
#             state_machine[dlci][STATE_DLC_PARAM_NEGOTIATED] = [SABM]
#             if VISUALIZE:
#                 vis.add_state(state2str(STATE_DLC_PARAM_NEGOTIATED))
#                 vis.add_tr(state2str(STATE_CTRL_SESSION), state2str(STATE_DLC_PARAM_NEGOTIATED), "PN")
#         else:
#             print(colored(" [Fail]", "red"))
#         time.sleep(0.5)

#         # --- 4. DLCI=n session establish (SABM/UA) ---
#         print(colored(f"(4/8) DLCI={dlci} session establishment (SABM/UA)"), end="", flush=True)
#         if sock:
#             sock2 = initiate_dlc(sock, dlci)
#             if sock2:
#                 print(colored(" [Success]", "green"))
#                 state_machine[dlci][STATE_DLC_ESTABLISHED] = [DISC, MSC]
#                 if VISUALIZE:
#                     vis.add_state(state2str(STATE_DLC_ESTABLISHED))
#                     vis.add_tr(state2str(STATE_DLC_PARAM_NEGOTIATED), state2str(STATE_DLC_ESTABLISHED), "SABM")
#                 sock2.close()

#         # --- 5. DLCI=n data session ready (MSC exchanged) ---
#         print(colored(f"(5/8) DLCI={dlci} data session ready (MSC exchanged)"), end="", flush=True)
#         sock, msc_ok = open_data_session(target_addr, dlci)
#         if sock:
#             print(colored(" [Success]", "green"))
#             state_machine[dlci][STATE_DATA_SESSION_READY] = [DATA, DISC]
#             if VISUALIZE:
#                 vis.add_state(state2str(STATE_DATA_SESSION_READY))
#                 vis.add_tr(state2str(STATE_DLC_ESTABLISHED), state2str(STATE_DATA_SESSION_READY), "MSC")
#             sock.close()
#         time.sleep(3)

#         # ---- (Optional: Advanced multi-DLCI, test response states, etc.) ----
#         # TODO: handle multi-DLCI, unsolicited PN from remote, etc.

#     except Exception as e:
#         print(f"[-] construct_sm: {e}")
#         # Optionally print state_machine for debugging
#         print(print_sm(state_machine))
#         if VISUALIZE:
#             vis.get_graph().draw("base_sm.png", prog='dot')
#         return None

#     # --- Pretty-print and visualize the base state machine ---
#     print(colored("\nBase State Machine:", "cyan"))
#     from pprint import pprint
#     pprint(print_sm(state_machine))

#     if VISUALIZE:
#         vis.get_graph().draw("base_sm.png", prog='dot')

#     return state_machine

def recv_pkt(sock):
    """
    Receive frame from socket
    
    Parameters
    ----------
     - sock : Bluetooth socket

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - [tuple] ([string] control type of frame, [bytes] received frame) 

    """
    conn_rsp, sock = inter_recv(sock)
    if conn_rsp == None:
        print('[*] recv failed.')
        return None, None
    else:  
        frame_pkt = FRAME_PKT(conn_rsp)
        control = frame_pkt.parse_pkt()
        return control, conn_rsp

def send_frame(sock, frame, ch, state, channel_to_ctrl, base_sm, ret_sm, path):
    """
    Send RFCOMM frame to target device.\n
    
    Test if sended frame triggers new state.\n

    If response is not DM, DISC, NSC, sended frame triggers new state.
    
    Parameters
    ----------
     - sock : Bluetooth socket
     - frame : [bytes] RFCOMM frame to send
     - ch : [int] target profile DLCI
     - state : [int] current state
     - channel_to_ctrl : [int] target profile DLCI
     - base_sm : base state machine
     - ret_sm : expanded state machine with new state
     - path : [function] transition function for source(current) state 

    Note
    ---------
     - transition function is defined in `modules.pairing`

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - [bool] True : new state found, False : no new state
    """
    global new_state
    global hidden_state_path
    global tmp_pkt
    global crash_cnt
    global pkt_cnt
    pkt_info = ""
    pkt_cnt += 1

    # [1] send frame to target device 
    if frame not in RFCOMM_CMD:
        tmp_pkt = frame.gen(transition=True)
        sock.send(tmp_pkt)
    else:
        tmp_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel_to_ctrl, transition=True, mx_type=frame)
        sock.send(tmp_pkt)

    # [2] print out sended frame information to log
    pkt_info = {}
    pkt_info['no'] = pkt_cnt
    pkt_info['protocol'] = 'RFCOMM'
    pkt_info['sended_time'] = str(datetime.now())
    pkt_info['payload'] = tmp_pkt
    pkt_info['crash'] = 'n'
    pkt_info['state'] = state2str(state)
    logger.inputQueue(pkt_info)

    # [3] Test if respond is received and new state is found
    try:
        rsp_type, conn_rsp = recv_pkt(sock)
        # not NSC
        if (rsp_type and (rsp_type != "DM" and rsp_type != "DISC")) and \
            (conn_rsp and conn_rsp[3] != 0x11) and \
            (frame not in base_sm[ch][state]):
            ret_sm[ch][state].append(frame)
            ret_sm[ch][new_state] = []
            hidden_state_path.append((path, tmp_pkt))
            vis.add_state(state2str(new_state))
            vis.add_tr(state2str(state),state2str(new_state), frame2str(frame))
            new_state += 1

    except:
        sock.close()
        return False
    return True


def expand_sm(sm, initial_channel, target_addr):
    """
    Expand base state machine to adaptive state machine for target.\n

    
    Parameters
    ----------
     - sm : base state machine
     - initial_channel : [int] target profile DLCI
     - target_addr : [string] MAC address of target device

    Note
    ---------
     - For more information of hidden state path, See global variable `hidden_state_path`

    Raises
    ----------
     - SMTraverseError

    Returns
    ----------
     - [tuple] (adaptive state machine, hidden state path)

    
    """
    global logger
    logger.inputQueue("******************Fuzzing stage 1***********************")
    ret = copy.deepcopy(sm)
    global new_state
    global hidden_state_path

    # [1] For each channel in base state machine,
    try:
        for ch in sm:

    # [2] Expand control channel state machine
            if ch == CTRL_CHANNEL:
                for state in sm[ch]:

        # [2-1] For each RFCOMM frame and command, Expand control channel SM
                    if state == CLOSED:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            # [2-1-1] Change socket state to CLOSED
                            sock = closed(target_addr)
                            if sock:
                            # [2-1-2] Send RFCOMM frame and expand SM
                                send_frame(sock, frame, ch,state,CTRL_CHANNEL, sm, ret, closed)
                                sock.close()

                                # ANOMALY DETECTION
                                sock = closed(target_addr)
                                if sock:
                                    sock.close()
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")
                                
                            # [2-1-3] if fuzzer cannot move to CLOSED state, raise SMTraverseError -> state machine violation
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                        print("[*] CLOSED done")


                    elif state == OPENED_CTRL_CH:
                        for frame in RFCOMM_CMD:
                            # [2-1-1] Change socket state to OPEN_CTRL_CH
                            sock = opened_ctrl_ch(target_addr)
                            if sock:
                            # [2-1-2] Send RFCOMM frame and expand SM
                                send_frame(sock, frame, ch, state,CTRL_CHANNEL, sm, ret, opened_ctrl_ch)
                                sock.close()

                                # ANOMALY DETECTION
                                sock = opened_ctrl_ch(target_addr)
                                if sock:
                                    sock.close()
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")

                            # [2-1-3] if fuzzer cannot move to OPEN_CTRL_CH state, raise SMTraverseError -> state machine violation
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                        print("[*] OPENED_CTRL_CH done")

    # [3] Expand target profile channel state machine
            elif ch == initial_channel:
                for state in sm[ch]:

        # [3-1] For each RFCOMM frame and command, Expand target profile channel SM
                    if state == CLOSED_NORMAL_CH:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            # [3-1-1] Change socket state to CLOSED_NORMAL_CH
                            sock = closed_normal_ch(target_addr, initial_channel)
                            if sock:
                            # [3-1-2] Send RFCOMM frame and expand SM
                                send_frame(sock, frame, ch, state, initial_channel, sm, ret, closed_normal_ch)
                                sock.close()

                                # ANOMALY DETECTION
                                sock = closed_normal_ch(target_addr, initial_channel)
                                if sock:
                                    sock.close()
                                else:
                                   raise SMTraverseError(f"cannot traverse {state2str(state)}") 

                            # [3-1-3] if fuzzer cannot move to CLOSED_NORMAL_CH state, raise SMTraverseError -> state machine violation
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                        print("[*] CLOSED_NORMAL_CH done")

                    elif state == OPENED_NORMAL_CH:
                        for frame in RFCOMM_CMD:
                            # [3-1-1] Change socket state to OPENED_NORMAL_CH
                            sock = open_normal_ch(target_addr, initial_channel)
                            if sock:
                            # [3-1-2] Send RFCOMM frame and expand SM
                                send_frame(sock, frame, ch, state, initial_channel, sm, ret, open_normal_ch)
                                sock.close()

                                # ANOMALY DETECTION
                                sock = open_normal_ch(target_addr, initial_channel)
                                if sock:
                                    sock.close()
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")

                            # [3-1-3] if fuzzer cannot move to OPENED_NORMAL_CH state, raise SMTraverseError -> state machine violation
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                        print("[*] OPENED_NORMAL_CH done")


                    elif state == OPENED_NORMAL_CH_WITH_MSC:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            # [3-1-1] Change socket state to OPENED_NORMAL_CH_WITH_MSC
                            sock, _ = open_normal_ch_with_msc(target_addr, initial_channel)
                            if sock:
                            # [3-1-2] Send RFCOMM frame and expand SM
                                send_frame(sock, frame, ch, state, initial_channel, sm, ret, open_normal_ch_with_msc)
                                sock.close()

                                # ANOMALY DETECTION
                                sock, _ = open_normal_ch_with_msc(target_addr, initial_channel)
                                if sock:
                                    sock.close()
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")

                            # [3-1-3] if fuzzer cannot move to OPENED_NORMAL_CH_WITH_MSC state, raise SMTraverseError -> state machine violation
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                        print("[*] OPENED_NORMAL_CH_WITH_MSC done")
    
    # [4] Expand other channel(non-target profile) state machine    
            else:
                for state in sm[ch]:

        # [4-1] For each RFCOMM frame and command, Expand non-target profile channel SM
                    if state == CLOSED_NORMAL_CH:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            # [4-1-1] Change socket state to CLOSED_NORMAL_CH
                            sock, _  = open_new_chan(target_addr, initial_channel)
                            if sock:
                            # [4-1-2] Send RFCOMM frame and expand SM
                                send_frame(sock, frame, ch, state, ch, sm, ret, open_new_chan)
                                sock.close()

                                # ANOMALY DETECTION
                                sock, _  = open_new_chan(target_addr, initial_channel)
                                if sock:
                                    sock.close()
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")

                            # [4-1-3] if fuzzer cannot move to CLOSED_NORMAL_CH state, raise SMTraverseError -> state machine violation
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                        print("[*] CLOSED_NORMAL_CH done")
                    elif state == OPENED_NORMAL_CH:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            # [4-1-1] Change socket state to OPENED_NORMAL_CH
                            sock , new_dlci= open_new_chan(target_addr, initial_channel)
                            if sock:
                                sock = establish_dlci(sock, new_dlci)
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                            # [4-1-2] Send RFCOMM frame and expand SM
                            if sock:
                                send_frame(sock, frame, ch, state, ch, sm, ret, establish_new_dlci)
                                sock.close()

                                # ANOMALY DETECTION
                                sock , new_dlci= open_new_chan(target_addr, initial_channel)
                                if sock:
                                    sock = establish_dlci(sock, new_dlci)
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")
                                if sock:
                                    sock.close()
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")

                            # [4-1-3] if fuzzer cannot move to OPENED_NORMAL_CH state, raise SMTraverseError -> state machine violation
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                        print("[*] OPENED_NORMAL_CH done")
                    elif state == OPENED_NORMAL_CH_WITH_MSC:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            # [4-1-1] Change socket state to OPENED_NORMAL_CH_WITH_MSC
                            sock , new_dlci= open_new_chan(target_addr, initial_channel)
                            if sock:
                                sock = establish_dlci(sock, new_dlci)
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                            if sock:
                                sock, msc = new_chan_msc(sock, new_dlci>>1, new_dlci&0b1)
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                            # [4-1-2] Send RFCOMM frame and expand SM
                            if sock:
                                send_frame(sock, frame, ch, state, ch, sm, ret, new_chan_msc)
                                sock.close()

                                # ANOMALY DETECTION
                                sock , new_dlci= open_new_chan(target_addr, initial_channel)
                                if sock:
                                    sock = establish_dlci(sock, new_dlci)
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")
                                if sock:
                                    sock, msc = new_chan_msc(sock, new_dlci>>1, new_dlci&0b1)
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")
                                if sock:
                                    sock.close()
                                else:
                                    raise SMTraverseError(f"cannot traverse {state2str(state)}")

                            # [4-1-3] if fuzzer cannot move to OPENED_NORMAL_CH_WITH_MSC state, raise SMTraverseError -> state machine violation
                            else:
                                raise SMTraverseError(f"cannot traverse {state2str(state)}")
                        print("[*] OPENED_NORMAL_CH_WITH_MSC done")
    
    # [5] Exception handling, if state machine violation is occured, print out crash log and return False.
    except Exception as e:
        print("[*] crash detected while expanding State Machine")
        print(f"[*] {e}")
        pprint(print_sm(ret))
        print(hidden_state_path)
        logger.inputQueue("crashed at : ")
        logger.inputQueue(tmp_pkt)
        logger.logUpdate()
        if VISUALIZE:
            vis.get_graph().draw("expanded_sm.png", prog='dot')
        
        return False
    pprint(print_sm(ret))
    print(hidden_state_path)
    
    # [6] Complete expand_sm logic. 
    logger.inputQueue("*******************Stage 1 complete****************************")
    logger.logUpdate()
    
    if VISUALIZE:
        vis.get_graph().draw("expanded_sm.png", prog='dot')
    return ret, hidden_state_path