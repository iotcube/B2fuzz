from modules import *
from .pairing import *
from collections import defaultdict
import copy
import os
from transitions.extensions import GraphMachine

class Visualize:
    def __init__(self) -> None:
        self.m = GraphMachine(model=self, graph_engine="pygraphviz", 
            states=["closed_state"],
            initial= "closed_state"
        )

    def add_state(self, state):
        self.m.add_state(state)

    def add_tr(self, src, dst, frame):
        self.m.add_transition(frame, src, dst)

vis = Visualize()

hidden_state_path = []


def delete_paired_dev(target_addr):
    os.system(f"bluetoothctl disconnect {target_addr}")
    os.system(f"bluetoothctl remove {target_addr}")

def state2str(state):
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
    return frame.name()



def construct_sm(target_addr, channel):
    ret = defaultdict(dict)
    try:
        # can connect
        sock = closed(target_addr)
        if sock:
            ret[CTRL_CHANNEL][CLOSED] = [SABM]
            sock.close()

        # can open ctrl channel
        sock = opened_ctrl_ch(target_addr)
        if sock:

            vis.add_state(state2str(OPENED_CTRL_CH))
            vis.add_tr(state2str(CLOSED), state2str(OPENED_CTRL_CH), frame2str(SABM))
            vis.add_tr(state2str(OPENED_CTRL_CH), state2str(CLOSED), frame2str(DISC))

            ret[CTRL_CHANNEL][OPENED_CTRL_CH] = [DISC, PN]
            sock.close()

        sock = closed_normal_ch(target_addr, channel)
        if sock:
            vis.add_state(state2str(CLOSED_NORMAL_CH))
            vis.add_tr(state2str(OPENED_CTRL_CH), state2str(CLOSED_NORMAL_CH), frame2str(PN))

            ret[channel][CLOSED_NORMAL_CH] = [SABM]
            if establish_dlci(sock, channel):

                vis.add_state(state2str(OPENED_NORMAL_CH))
                vis.add_tr( state2str(CLOSED_NORMAL_CH),state2str(OPENED_NORMAL_CH), frame2str(SABM))
                vis.add_tr(state2str(OPENED_NORMAL_CH), state2str(CLOSED_NORMAL_CH), frame2str(DISC))

                ret[channel][OPENED_NORMAL_CH] = [DISC, MSC]
            sock.close()


        sock, _ = open_normal_ch_with_msc(target_addr, channel)
        if sock:

            vis.add_state(state2str(OPENED_NORMAL_CH_WITH_MSC))
            vis.add_tr(state2str(OPENED_NORMAL_CH_WITH_MSC),state2str(CLOSED_NORMAL_CH), frame2str(DISC))
            vis.add_tr(state2str(OPENED_NORMAL_CH), state2str(OPENED_NORMAL_CH_WITH_MSC), frame2str(MSC))
            vis.add_tr(state2str(OPENED_NORMAL_CH_WITH_MSC), state2str(OPENED_NORMAL_CH_WITH_MSC), frame2str(DATA))

            ret[channel][OPENED_NORMAL_CH_WITH_MSC] = [DATA, DISC]
            sock.close()

        sock, new_dlci = open_new_chan(target_addr, channel)
        if sock:
            # ADD new channel SM
            vis.add_state(state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1))
            vis.add_tr(state2str(OPENED_CTRL_CH), state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1), frame2str(PN))

            ret[new_dlci>>1][CLOSED_NORMAL_CH] = [SABM]
            sock = establish_new_dlci(sock, new_dlci)
            if sock:
                vis.add_state(state2str(OPENED_NORMAL_CH)+str(new_dlci>>1))
                vis.add_tr(state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1),state2str(OPENED_NORMAL_CH)+str(new_dlci>>1), frame2str(SABM))
                vis.add_tr(state2str(OPENED_NORMAL_CH)+str(new_dlci>>1), state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1), frame2str(DISC))
                ret[new_dlci>>1][OPENED_NORMAL_CH] = [DISC, MSC]
            sock, msc = new_chan_msc(sock, new_dlci>>1, new_dlci&0b1)
            if msc:
                vis.add_state(state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1))
                vis.add_tr(state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1),state2str(CLOSED_NORMAL_CH)+str(new_dlci>>1), frame2str(DISC))
                vis.add_tr(state2str(OPENED_NORMAL_CH)+str(new_dlci>>1), state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1), frame2str(MSC))
                vis.add_tr(state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1), state2str(OPENED_NORMAL_CH_WITH_MSC)+str(new_dlci>>1), frame2str(DATA))
                ret[new_dlci>>1][OPENED_NORMAL_CH_WITH_MSC] = [DATA, DISC]
            sock.close()
    except:
        pass
    pprint(print_sm(ret))
    vis.get_graph().draw("base_sm.png", prog='dot')
    return ret


def print_sm(sm):
    ret = {}
    for ch in sm:
        per_ch_sm = {}
        for state in sm[ch]:
            per_ch_sm[state2str(state)] = [f.name() for f in sm[ch][state]]
        ret[f"channel{ch}"] = per_ch_sm
    return ret
    
def recv_pkt(sock):
    conn_rsp, sock = inter_recv(sock)
    if conn_rsp == None:
        print('[*] recv failed.')
        return None, None
    else:  
        frame_pkt = FRAME_PKT(conn_rsp)
        control = frame_pkt.parse_pkt()
        return control, conn_rsp

def send_frame(sock, frame, ch, state, channel_to_ctrl, base_sm, ret_sm, path):
    global new_state
    global hidden_state_path
    if frame not in RFCOMM_CMD:
        sock.send(frame.gen())
    else:
        sock.send(UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel_to_ctrl, transition=True, mx_type=frame))
    try:
        rsp_type, conn_rsp = recv_pkt(sock)
        # not NSC
        if (rsp_type and (rsp_type != "DM" and rsp_type != "DISC")) and \
            (conn_rsp and conn_rsp[3] != 0x11) and \
            (frame not in base_sm[ch][state]):
            ret_sm[ch][state].append(frame)
            ret_sm[ch][new_state] = []
            hidden_state_path.append([(path, frame)])
            vis.add_state(state2str(new_state))
            vis.add_tr(state2str(state),state2str(new_state), frame2str(frame))
            new_state += 1

    except:
        sock.close()
        return False
    return True


def expand_sm(sm, initial_channel, target_addr):
    ret = copy.deepcopy(sm)
    global new_state
    try:
        for ch in sm:
            if ch == CTRL_CHANNEL:
                for state in sm[ch]:
                    if state == CLOSED:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            sock = closed(target_addr)
                            if sock and send_frame(sock, frame, ch,state,CTRL_CHANNEL, sm, ret, closed):
                                sock.close()
                        print("[*] CLOSED done")


                    elif state == OPENED_CTRL_CH:
                        for frame in RFCOMM_CMD:
                            sock = opened_ctrl_ch(target_addr)
                            if sock and send_frame(sock, frame, ch, state,CTRL_CHANNEL, sm, ret, opened_ctrl_ch):
                                sock.close()
                        print("[*] OPENED_CTRL_CH done")


            elif ch == initial_channel:
                for state in sm[ch]:
                    if state == CLOSED_NORMAL_CH:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            sock = closed_normal_ch(target_addr, initial_channel)
                            if sock and send_frame(sock, frame, ch, state, initial_channel, sm, ret, closed_normal_ch):
                                sock.close()
                        print("[*] CLOSED_NORMAL_CH done")

                    elif state == OPENED_NORMAL_CH:
                        for frame in RFCOMM_CMD:
                            sock = open_normal_ch(target_addr, initial_channel)
                            if sock and send_frame(sock, frame, ch, state, initial_channel, sm, ret, open_normal_ch):
                                sock.close()
                        print("[*] OPENED_NORMAL_CH done")


                    elif state == OPENED_NORMAL_CH_WITH_MSC:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            sock, _ = open_normal_ch_with_msc(target_addr, initial_channel)
                            if sock and send_frame(sock, frame, ch, state, initial_channel, sm, ret, open_normal_ch_with_msc):
                                sock.close()
                        print("[*] OPENED_NORMAL_CH_WITH_MSC done")
            else:
                for state in sm[ch]:
                    if state == CLOSED_NORMAL_CH:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            sock = open_new_chan(target_addr, initial_channel)
                            if sock and send_frame(sock, frame, ch, state, ch, sm, ret, open_new_chan):
                                sock.close()
                        print("[*] CLOSED_NORMAL_CH done")
                    elif state == OPENED_NORMAL_CH:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            sock , new_dlci= open_new_chan(target_addr, initial_channel)
                            if sock:
                                sock = establish_dlci(sock, new_dlci)
                            if sock and send_frame(sock, frame, ch, state, ch, sm, ret, open_new_chan):
                                sock.close()
                        print("[*] OPENED_NORMAL_CH done")
                    elif state == OPENED_NORMAL_CH_WITH_MSC:
                        for frame in RFCOMM_FRAME + RFCOMM_CMD:
                            sock , new_dlci= open_new_chan(target_addr, initial_channel)
                            if sock:
                                sock = establish_dlci(sock, new_dlci)
                            if sock:
                                sock, msc = new_chan_msc(sock, new_dlci>>1, new_dlci&0b1)
                            if sock and send_frame(sock, frame, ch, state, ch, sm, ret, open_new_chan):
                                sock.close()
                        print("[*] OPENED_NORMAL_CH_WITH_MSC done")
    except:
        pprint(print_sm(ret))
        print(hidden_state_path)
        vis.get_graph().draw("expanded_sm.png", prog='dot')
        return False
    pprint(print_sm(ret))
    print(hidden_state_path)
    vis.get_graph().draw("expanded_sm.png", prog='dot')