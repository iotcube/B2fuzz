"""
construct_sm.py

Constructs a RFCOMM channel-specific state machine for a target Bluetooth device,
according to the Bluetooth SIG RFCOMM Test Suite (TS) procedures.

Uses state constants, frame/command definitions from state.py,
and message sequence logic from testsuite.py.
Supports optional graph visualization of the resulting state machine.
"""

from lib.btpkt import FRAME_PKT, inter_recv
from lib.state import * 
from termcolor import colored
import time
import copy
import os, sys
from transitions.extensions import GraphMachine
import bluetooth
import traceback

class SM:
    pass

def print_sm(machine):
    """
    Converts a GraphMachine object into a simple dictionary for printing.
    """
    if not isinstance(machine, GraphMachine):
        return {}
    
    sm_dict = {}
    for state in machine.states:
        sm_dict[state] = [t.trigger for t in machine.get_triggers(state)]
    return sm_dict

def construct_sm(target_addr, target_channels=None, VISUALIZE=True, vis_path="rfcomm_fsm.png"):
    """
    Build the RFCOMM state machine by running test suites and collecting path data.
    Only successful transitions and states are included in the final graph.
    """
    from modules.testsuite import (
        tc_BV_01_C, tc_BV_04_C, tc_BV_05_C, tc_BV_07_C,
        tc_BV_11_C, tc_BV_13_C, tc_BV_14_C, tc_BV_17_C,
        tc_BV_19_C, tc_BV_21_C, tc_BV_22_C, tc_BV_25_C
    )

    if target_channels is None:
        target_channels = [1]

    # --- State Machine Initialization ---
    dummy_model = SM()
    initial_state = state_name(StateName.SESS_OPEN)
    machine = GraphMachine(
        model=dummy_model,
        states=[initial_state],
        initial=initial_state,
        auto_transitions=False,
        show_conditions=True,
        use_pygraphviz=True,
    )

    # --- THIS IS THE NEW STRATEGY: Track added transitions ourselves ---
    added_transitions = set()

    def add_transitions_from_path(path):
        """Helper function to add successful transitions from a path list to the machine."""
        if not path: return
        for src, trigger, dest, success in path:
            if not success:
                continue
            
            # Create a unique identifier for this transition
            transition_tuple = (src, trigger, dest)
            
            # *** THIS IS THE FIX: Check our own set, not the machine object ***
            if transition_tuple in added_transitions:
                continue # Skip if we've already added this exact transition

            # Add states if they don't exist
            if src not in machine.states:
                machine.add_state(src)
            if dest not in machine.states:
                machine.add_state(dest)
            
            # Add the new transition and record it
            machine.add_transition(trigger=trigger, source=src, dest=dest)
            added_transitions.add(transition_tuple)

    # --- Test Execution and State Machine Construction ---
    sock = None
    open_dlci_set = set()
    try:
        # 1. Session-level open
        path, sock = tc_BV_01_C(target_addr)
        add_transitions_from_path(path)
        if not sock:
            print(colored("[!] Session initialization failed. Aborting.", "red"))
            return None

        # 2. Session-level tests
        path, sock = tc_BV_11_C(sock, target_addr)
        add_transitions_from_path(path)
        
        path, sock = tc_BV_25_C(sock, target_addr)
        add_transitions_from_path(path)

        # 3. Loop through each target channel and run DLCI-specific tests
        for dlci in target_channels:
            print(colored(f"\n=== [DLCI {dlci}] Sequence Start ===", "magenta"))
            
            path, sock = tc_BV_05_C(sock, target_addr, dlci)
            add_transitions_from_path(path)
            
            # Check if the DLCI was successfully opened before proceeding
            if state_name(StateName.DATA_OPEN, dlci) in machine.states:
                open_dlci_set.add(dlci)
            else:
                print(colored(f"[!] DLCI {dlci} failed to open. Skipping to next.", "red"))
                continue

            # Run tests that require an open DLCI
            path, sock = tc_BV_13_C(sock, target_addr, dlci, open_dlci_set)
            add_transitions_from_path(path)
            
            path, sock = tc_BV_14_C(sock, target_addr, dlci, open_dlci_set)
            add_transitions_from_path(path)
            
            path, sock = tc_BV_17_C(sock, target_addr, dlci, open_dlci_set)
            add_transitions_from_path(path)
            
            path, sock = tc_BV_19_C(sock, target_addr, dlci, open_dlci_set)
            add_transitions_from_path(path)
            
            path, sock = tc_BV_21_C(sock, target_addr, dlci, open_dlci_set)
            add_transitions_from_path(path)
            
            path, sock = tc_BV_22_C(sock, target_addr, dlci, open_dlci_set)
            add_transitions_from_path(path)

            path, sock = tc_BV_07_C(sock, target_addr, dlci, open_dlci_set)
            add_transitions_from_path(path)

            print(colored(f"=== [DLCI {dlci}] Sequence End ===\n", "magenta"))

        path = tc_BV_04_C(sock, target_addr, [])
        add_transitions_from_path(path)
        sock = None

    except Exception as e:
        print(colored(f"[-] A critical error occurred in construct_sm: {e}", "red"))
        traceback.print_exc()
        if sock: sock.close()

    print(colored("\n[Result] RFCOMM State Machine Construction Complete.", "cyan"))

    # 5. Visualization (optional)
    if VISUALIZE:
        try:
            # The machine object now holds the graph of all successful state transitions.
            machine.get_graph().draw(vis_path, prog='dot')
            print(colored(f"[+] State machine diagram saved to {vis_path}", "green"))
        except Exception as e:
            print(colored(f"[!] Visualization failed. Ensure pygraphviz is installed (`pip install pygraphviz`): {e}", "red"))

    return machine

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