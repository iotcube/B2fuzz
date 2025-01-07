import time
from lib import *
from layer.rfcomm.const import RFCOMM_PSM
from layer.rfcomm.types.dm import DM
from layer.rfcomm.types.disc import DISC
from layer.rfcomm.types.sabm import SABM
from layer.rfcomm.types.ua import UA
from layer.rfcomm.types.uih import UIH
from layer.rfcomm.types.uih import DATA

STATE_LIST = [RFCOMM_CLOSED_STATE, RFCOMM_TERM_WAIT_SEC_CHECK_STATE, RFCOMM_OPENED_STATE, RFCOMM_DISC_WAIT_UA_STATE]

# event 발생 frame은 총 6개, BluDroid의 유효 frame의 여집합
bluedroid_hidden_state = {
    RFCOMM_CLOSED_STATE: [ DM, UA ],
    RFCOMM_TERM_WAIT_SEC_CHECK_STATE: [ DM, DISC, UA ],
    RFCOMM_OPENED_STATE: [ DM, DISC, UA ],
    RFCOMM_DISC_WAIT_UA_STATE: [ DM, DISC, SABM, UIH ],
}

# BlueDroid 정적분석을 통해 발견된 frame
NORMAL_STATE_FRAME = {
    RFCOMM_CLOSED_STATE: [ SABM, DATA, UIH, DISC ],
    RFCOMM_TERM_WAIT_SEC_CHECK_STATE: [ UIH, SABM, DATA ],
    RFCOMM_OPENED_STATE: [ UIH, SABM, DATA ],
    RFCOMM_DISC_WAIT_UA_STATE: [ UA, DATA ]
}

def state2str(state):
    if state == RFCOMM_CLOSED_STATE:
        return 'CLOSED'
    elif state== RFCOMM_TERM_WAIT_SEC_CHECK_STATE:
        return 'TERM_WAIT_SEC_CHECK'
    elif state == RFCOMM_OPENED_STATE:
        return 'OPEN'
    elif state== RFCOMM_DISC_WAIT_UA_STATE:
        return 'DISC_WAIT_UA'
    else:
        return 'Hidden'+str(state - 0x7)

def frame2str(frame):
    if frame == DM:
        return 'DM'
    elif frame == DISC:
        return 'DISC'
    elif frame == SABM:
        return 'SABM'
    elif frame == UA:
        return 'UA'
    elif frame == UIH:
        return 'UIH'
    elif frame == DATA:
        return 'DATA'
    else:
        return 'Wrong'

def parse_adaptive_state(state):
    ret = {}
    for idx, start_state in enumerate(state):
        frame_types = {}
        if start_state < 0x7:
            for normal_state in NORMAL_STATE_FRAME[start_state]:
                frame_types[frame2str(normal_state)] = state2str(STATE_LIST[(idx+1)%len(STATE_LIST)])
            for hidden_state in bluedroid_hidden_state[start_state]:
                if len(state[start_state]) != 0:
                    frame_types[frame2str(hidden_state)] = 'hidden state'
        else:
            for hs in [DM, DISC, SABM, UA, UIH, DATA]:
                if hs in state[start_state]:
                    frame_types[frame2str(hs)] = 'hidden state'
        if len(frame_types) == 0:
            ret[state2str(start_state)] = "[]"
        else:
            ret[state2str(start_state)] = frame_types

    return ret

def send_frame(sock, frame_type, mx_type=None):
    count = 0
    while count < 3:
        try:
            if frame_type == UIH:
                test = bytes(frame_type.gen(mx_type))
                sock.send(test)
            else:
                sock.send(bytes(frame_type.gen()))
            conn_rsp, sock = inter_recv(sock)
            if conn_rsp == None:
                print('[*] recv failed.')
            else:  
                frame_pkt = FRAME_PKT(conn_rsp)
                control = frame_pkt.parse_pkt()
                return control
        except Exception as e:
            conn_rsp = ""
            count += 1
            
        if conn_rsp == "":
            continue
    return None

def closed(target_addr):
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    return sock

def term_wait_sec(target_addr):
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    sock.send(bytes(SABM.gen(transition=True)))
    return sock

def opened_state(target_addr):
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    sock.send(bytes(SABM.gen(transition=True)))
    sock.send(bytes(SABM.gen(transition=True)))
    return sock

def disc_wait_ua(target_addr):
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    sock.send(bytes(SABM.gen(transition=True)))
    sock.send(bytes(SABM.gen(transition=True)))
    sock.send(bytes(DISC.gen(transition=True)))
    return sock

hidden_state_path = []

def hidden(target_addr, state):
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    for f in hidden_state_path[state - 0x7]:
        #print(f)
        sock.send(bytes(f.gen(transition=True)))
    return sock

def construct_android_adaptive_sm(target_addr):
    print('Construct adaptive state machine...')
    hidden_state = 0x7
    global bluedroid_hidden_state
    adaptive_state_frame = {
        RFCOMM_CLOSED_STATE: [],
        RFCOMM_TERM_WAIT_SEC_CHECK_STATE: [],
        RFCOMM_OPENED_STATE: [],
        RFCOMM_DISC_WAIT_UA_STATE: []
    }
    for state in STATE_LIST:
        if state == RFCOMM_CLOSED_STATE:
            for frame in bluedroid_hidden_state[state]:
                sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
                sock.connect((target_addr, RFCOMM_PSM))
                res = send_frame(sock, frame)
                if res:
                    if res != 'DM':
                        adaptive_state_frame[RFCOMM_CLOSED_STATE].append(frame)
                        adaptive_state_frame[hidden_state] = []
                        hidden_state += 1
                        hidden_state_path.append([frame])
                sock.close()
                time.sleep(0.5)
            print('[*] CLOSED done')
        elif state == RFCOMM_TERM_WAIT_SEC_CHECK_STATE:
            for frame in bluedroid_hidden_state[state]:
                sock = term_wait_sec(target_addr)
                res = send_frame(sock, frame)
                if res:
                    if res != 'DM':
                        adaptive_state_frame[RFCOMM_TERM_WAIT_SEC_CHECK_STATE].append(frame)
                        adaptive_state_frame[hidden_state] = []
                        hidden_state += 1
                        hidden_state_path.append([SABM, frame])
                sock.close()
                time.sleep(0.5)
            print('[*] TERM WAIT SEC CHECK done')
        elif state == RFCOMM_OPENED_STATE:
            for frame in bluedroid_hidden_state[state]:
                sock = opened_state(target_addr)
                res =  send_frame(sock, frame)
                if res:
                    if res != 'DM':
                        adaptive_state_frame[RFCOMM_OPENED_STATE].append(frame)
                        adaptive_state_frame[hidden_state] = []
                        hidden_state += 1
                        hidden_state_path.append([SABM,SABM, frame])
                sock.close()
                time.sleep(0.5)
            print('[*] OPENED done')
        elif state == RFCOMM_DISC_WAIT_UA_STATE:
            for frame in bluedroid_hidden_state[state]:
                sock = disc_wait_ua(target_addr)
                res = send_frame(sock, frame)
                if res:
                    if res != 'DM':
                        adaptive_state_frame[RFCOMM_DISC_WAIT_UA_STATE].append(frame)
                        adaptive_state_frame[hidden_state] = []
                        hidden_state += 1
                        hidden_state_path.append([SABM,SABM,DISC,frame])
                sock.close()
                time.sleep(0.5)
            print('[*] DISC WAIT UA done')

    # pruning hiddend states

    all_frame = [DM, DISC, SABM, UA, UIH, DATA]
    for state in range(0x7, hidden_state):
        for frame in all_frame:
            sock = hidden(target_addr, state)
            res = send_frame(sock, frame)
            if res:
                print("[-] state: "+ state2str(state)+", "+"res: "+res)
                if res != 'DM':
                    adaptive_state_frame[state].append(frame)
            sock.close()
            time.sleep(0.5)
        print('[*] '+state2str(state)+' done')
    return adaptive_state_frame