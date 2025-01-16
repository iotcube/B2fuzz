from modules import *
from collections import defaultdict

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

def construct_sm(target_addr, channel):
    ret = defaultdict(dict)
    try:
        # can connect
        sock = closed(target_addr)
        if sock:
            ret[CTRL_CHANNEL][CLOSED] = []
            sock.close()

        # can open ctrl channel
        sock = opened_ctrl_ch(target_addr)
        if sock:
            ret[CTRL_CHANNEL][OPENED_CTRL_CH] = []
            sock.close()

        sock = msc_state(target_addr, channel)
        if sock:
            ret[channel][CLOSED_NORMAL_CH] = []
            if establish_dlci(sock, channel):
                ret[channel][OPENED_NORMAL_CH] = []
            sock.close()


        sock, _ = open_ch_n(target_addr, channel)
        if sock:
            ret[channel][OPENED_NORMAL_CH_WITH_MSC] = []
            sock.close()

        sock, new_dlci = open_new_chan(target_addr, channel)
        if sock:
            # ADD new channel SM
            ret[new_dlci>>1][CLOSED_NORMAL_CH] = []
            sock = establish_new_dlci(sock, new_dlci)
            if sock:
                ret[new_dlci>>1][OPENED_NORMAL_CH] = []
            sock, msc = new_chan_msc(sock, new_dlci>>1, new_dlci&0b1)
            if msc:
                ret[new_dlci>>1][OPENED_NORMAL_CH_WITH_MSC] = []
            sock.close()
    except:
        pass
    pprint(print_sm(ret))    
    return ret


def print_sm(sm):
    ret = {}
    for ch in sm:
        per_ch_sm = {}
        for state in sm[ch]:
            per_ch_sm[state2str(state)] = sm[ch][state]
        ret[f"channel{ch}"] = per_ch_sm
    return ret
    

