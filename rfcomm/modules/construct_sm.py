#from modules import *
from .pairing import *
from .mutation_new import *
from collections import defaultdict
import time
import copy
import os
from transitions.extensions import GraphMachine

VISUALIZE = 0
"""
Flag value to print out base, adaptive state machine.\n
0 -> disable\n
1 -> enable

if enabled, 
`base_sm.png`, `expanded_sm.png` is came out
"""

tmp_pkt = None
"""
tmp variable to store sended frame.
"""


class Visualize:
    """
    Rapper class of `GraphMachine`.\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
     self.m : `GraphMachine` 

    Methods
    ----------
     - `.add_state("state name")`
     - `.add_tr("transition name")`
    """
    def __init__(self) -> None:
        self.m = GraphMachine(model=self, graph_engine="pygraphviz", 
            states=["closed_state"],
            initial= "closed_state"
        )

    def add_state(self, state):
        """
        Add state in the `GraphMachine`

        Parameters
        ----------
         - state : [string] state name

        Raises
        ----------
         - 

        Returns
        ----------
         -
        """
        self.m.add_state(state)

    def add_tr(self, src, dst, frame):
        """
        Add transition in the `GraphMachine`

        Parameters
        ----------
         - src : [string] source state 
         - dst : [string] destination state
         - frame : [string] frame name(means transition)

        Raises
        ----------
         - 

        Returns
        ----------
         -
        """
        self.m.add_transition(frame, src, dst)

class SMTraverseError(Exception):
    """
    Error for state transition violation\n

    This error is raised when base state transition is not performed.\n

    Parameters
    ----------
     -
    
    Attributes
    ----------
     self.msg : [string] error message
    """
    def __init__(self, msg):
        self.msg = msg
    
    def __str__(self):
        return self.msg

vis = Visualize()
"""
Visualize class variable for drawing state machine.
"""

hidden_state_path = []
"""
[List of tuple] list for storing new(hidden) state path.\n

Note
--------
 - `hidden_state_path[i][0]` : transition function for source state.
 - `hidden_state_path[i][1]` : [bytes] frame for transition to new state.
 - transition function is defined in `modules.pairing`

See also
---------
 - `modules.construct_sm.expand_sm`
 - `modules.mutation_new.new_state_fuzzing`
"""

def delete_paired_dev(target_addr):
    """
    Not used
    """
    os.system(f"bluetoothctl disconnect {target_addr}")
    os.system(f"bluetoothctl remove {target_addr}")

def state2str(state):
    """
        Translate state code to string

        Parameters
        ----------
         - state : [int] State code defined in `modules.pairing`

        Raises
        ----------
         - 

        Returns
        ----------
         - [string] Name of each state
    """
    if state == CLOSED:
        return "closed_state"
    elif state == OPENED_CTRL_CH:
        return "opened_ctrl_channel_state"
    elif state == CLOSED_NORMAL_CH:
        return "closed normal ch"
    elif state == OPENED_NORMAL_CH:
        return "opened_normal_channel_state"
    elif state == OPENED_NORMAL_CH_WITH_MSC:
        return "opened normal channel(after msc)"
    else:
        return f"new state{state - 4}"

def frame2str(frame):
    """
        Translate frame to string

        Parameters
        ----------
         - frame : RFCOMM frame defined in `layer.rfcomm.types`

        Raises
        ----------
         - 

        Returns
        ----------
         - [string] Name of each frame
    """
    return frame.name()



def construct_sm(target_addr, channel):
    """
    Construct base state machine for target device.\n

    Parameters
    ----------
     - target_addr : [string] Mac address for target device
     - channel : [int] target profile number (DLCI)

    Raises
    ----------
     - 

    Returns
    ----------
     - [dictionary] base state machine

    Reference
    ----------
    Bluetoooth SIG (2024) RFCOMM Bluetooth Test Suite
    """

    ret = defaultdict(dict)
    try:
        # [1] Test RFCOMM initial state (CLOSED state)
        sock = closed(target_addr)
        if sock:
            ret[CTRL_CHANNEL][CLOSED] = [SABM]
            sock.close()

        time.sleep(5)

        # [2] test opening controle channel(DLCI=0)
        # See RFCOMM/DEVA/RFC/BV-01-C in Test suit
        sock = opened_ctrl_ch(target_addr)
        if sock:

            vis.add_state(state2str(OPENED_CTRL_CH))
            vis.add_tr(state2str(CLOSED), state2str(OPENED_CTRL_CH), frame2str(SABM))
            vis.add_tr(state2str(OPENED_CTRL_CH), state2str(CLOSED), frame2str(DISC))

            ret[CTRL_CHANNEL][OPENED_CTRL_CH] = [DISC, PN]
            sock.close()

        time.sleep(5)

        # [3] test PN negotiation is possible
        # See RFCOMM/DEVA/RFC/BV-05-C in Test suit
        sock = closed_normal_ch(target_addr, channel)
        time.sleep(5)
        if sock:
            vis.add_state(state2str(CLOSED_NORMAL_CH))
            vis.add_tr(state2str(OPENED_CTRL_CH), state2str(CLOSED_NORMAL_CH), frame2str(PN))

        # [4] test opening DLCI for target profile.
        # See RFCOMM/DEVA/RFC/BV-05-C in Test suit
            ret[channel][CLOSED_NORMAL_CH] = [SABM]
            if establish_dlci(sock, channel):

                vis.add_state(state2str(OPENED_NORMAL_CH))
                vis.add_tr( state2str(CLOSED_NORMAL_CH),state2str(OPENED_NORMAL_CH), frame2str(SABM))
                vis.add_tr(state2str(OPENED_NORMAL_CH), state2str(CLOSED_NORMAL_CH), frame2str(DISC))

                ret[channel][OPENED_NORMAL_CH] = [DISC, MSC]
            sock.close()

        time.sleep(5)

        # [5] test MSC exchange.
        # See RFCOMM/DEVA-DEVB/RFC/BV-22-C in Test suit
        sock, _ = open_normal_ch_with_msc(target_addr, channel)
        if sock:

            vis.add_state(state2str(OPENED_NORMAL_CH_WITH_MSC))
            vis.add_tr(state2str(OPENED_NORMAL_CH_WITH_MSC),state2str(CLOSED_NORMAL_CH), frame2str(DISC))
            vis.add_tr(state2str(OPENED_NORMAL_CH), state2str(OPENED_NORMAL_CH_WITH_MSC), frame2str(MSC))
            vis.add_tr(state2str(OPENED_NORMAL_CH_WITH_MSC), state2str(OPENED_NORMAL_CH_WITH_MSC), frame2str(DATA))

            ret[channel][OPENED_NORMAL_CH_WITH_MSC] = [DATA, DISC]
            sock.close()

        time.sleep(5)

        # [6] Test if another DLCI opening request is recved.
        sock, new_dlci = open_new_chan(target_addr, channel)
        time.sleep(5)
        if sock:
            vis.add_state(state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1))
            vis.add_tr(state2str(OPENED_CTRL_CH), state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1), frame2str(PN))

            ret[new_dlci>>1][CLOSED_NORMAL_CH] = [SABM]



        # [7] test opening DLCI for target profile.
        # See RFCOMM/DEVB/RFC/BV-06-C in Test suit
            sock = establish_new_dlci(sock, new_dlci)
            time.sleep(5)
            if sock:
                vis.add_state(state2str(OPENED_NORMAL_CH)+str(new_dlci>>1))
                vis.add_tr(state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1),state2str(OPENED_NORMAL_CH)+str(new_dlci>>1), frame2str(SABM))
                vis.add_tr(state2str(OPENED_NORMAL_CH)+str(new_dlci>>1), state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1), frame2str(DISC))
                ret[new_dlci>>1][OPENED_NORMAL_CH] = [DISC, MSC]



        # [8] test MSC exchange.
        # See RFCOMM/DEVA-DEVB/RFC/BV-22-C in Test suit
            sock, msc = new_chan_msc(sock, new_dlci>>1, new_dlci&0b1)
            if msc:
                vis.add_state(state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1))
                vis.add_tr(state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1),state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1), frame2str(DISC))
                vis.add_tr(state2str(OPENED_NORMAL_CH)+str(new_dlci>>1), state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1), frame2str(MSC))
                vis.add_tr(state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1), state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1), frame2str(DATA))
                ret[new_dlci>>1][OPENED_NORMAL_CH_WITH_MSC] = [DATA, DISC]
            sock.close()

        time.sleep(5)
    except:
        pass

    # [9] print out base state machine
    pprint(print_sm(ret))

    # [10] print out visualized base state machine
    if VISUALIZE:
        vis.get_graph().draw("base_sm.png", prog='dot')
    
    return ret


def print_sm(sm):
    """
    Change state, frame in state machine into string.

    Parameters
    ----------
     - sm : state machine

    Raises
    ----------
     - 

    Returns
    ----------
     - [dictionary] state machine(printable)

    """
    ret = {}
    for ch in sm:
        per_ch_sm = {}
        for state in sm[ch]:
            per_ch_sm[state2str(state)] = [f.name() for f in sm[ch][state]]
        ret[f"channel{ch}"] = per_ch_sm
    return ret
    
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