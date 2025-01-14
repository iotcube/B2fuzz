from datetime import datetime
from pprint import pprint
from modules import *
from lib import *
from time import sleep
from layer.rfcomm.const import RFCOMM_PSM
from layer.rfcomm.types.dm import DM
from layer.rfcomm.types.disc import DISC
from layer.rfcomm.types.sabm import SABM
from layer.rfcomm.types.ua import UA
from layer.rfcomm.types.uih import UIH
from layer.rfcomm.types.uih import DATA
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

CLOSED = 0
OPENED_CTRL_CH = 1
MSC_STATE_SLAVE = 2
MSC_STATE_MASTER = 3
OPENED_CH_N = 4

CTRL_CHANNEL = 0

RFCOMM_FRAME = [DM, DISC, SABM, UA, UIH, DATA]

BASE_SM = {
    CLOSED: [SABM],
    OPENED_CTRL_CH: [UIH],
    MSC_STATE_SLAVE: [UIH],
    MSC_STATE_MASTER: [UIH],
    OPENED_CH_N: []
}

sm_path = []

def closed(target_addr):
    global ctrl_current_state
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    return sock

def opened_ctrl_ch(target_addr):
    global ctrl_current_state
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    sock.send(SABM.gen(channel=CTRL_CHANNEL, transition=True))
    conn_rsp, sock = inter_recv(sock)
    if conn_rsp == None:
        print('[*] recv failed.')
        return False
    else:  
        frame_pkt = FRAME_PKT(conn_rsp)
        res = frame_pkt.parse_pkt()
        if res:
            if res != "UA":
                print(f"[*] cannot open channel0")
                return False
    return sock

"""
return (sock, is_master)
"""
def msc_state(target_addr, channel):
    # enable ctrl channel
    global ctrl_current_state
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    sock.send(SABM.gen(channel=CTRL_CHANNEL, transition=True))
    
    conn_rsp, sock = inter_recv(sock)
    if conn_rsp == None:
        print('[*] recv failed.')
        return False
    else:  
        frame_pkt = FRAME_PKT(conn_rsp)
        res = frame_pkt.parse_pkt()
        if res:
            if res != "UA":
                print(f"[*] cannot open channel{channel}")
                return False
    sock.send(UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel, transition=True, mx_type=PN))
    sock.send(SABM.gen(channel=channel, transition=True))
    try:
        while True:
            conn_rsp, sock = inter_recv(sock)
            frame_pkt = FRAME_PKT(conn_rsp)
            res = frame_pkt.parse_pkt()
            if res:
                if res == "UA":
                    break
                elif res == "UIH":
                    continue
                else:
                    print(f"[*] cannot open channel{channel}")
                    return False
    except:
        print(f"[*] cannot open channel{channel}")
        return False

    #try:    
    #    while True:
    #        conn_rsp, sock = inter_recv(sock)
    #        if conn_rsp[3] == 0xe3 or conn_rsp[3] == 0xe1:
    #            sock.send(b'\x03' + conn_rsp[1:-1]+b"\x70")
    #            sleep(0.1)
    #            break
    #except:
    #    print("NO MSC")
    return sock 


def open_ch_n(target_addr, channel):
    sock= msc_state(target_addr, channel)
    if sock:
        sock.send(UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel, transition=True, mx_type=MSC))
        
        try:
            while True:
                conn_rsp, sock = inter_recv(sock)
                if conn_rsp[3] == 0xe3:
                    sock.send(b'\x03' + conn_rsp[1:3]+b"\xe1"+conn_rsp[4:-1]+b"\xaa")
                elif conn_rsp[3] == 0xe1:
                    break
        except:
            print("[*] cannot MSC")

        # Credite
        sock.send(DATA.gen(transition=True, channel=channel))
        is_new_chan = False
        try:
            while True:
                conn_rsp, sock = inter_recv(sock)
                if conn_rsp[3] == 0x83: # Onother PN?
                    #sock.send(DATA.gen(transition=True, channel=channel))    
                    resp_rsp2 = b'\x03' + conn_rsp[1:]
                    resp_rsp2 = resp_rsp2[:3]+b"\x81"+resp_rsp2[4:]
                    resp_rsp2 = resp_rsp2[:6]+b"\xe0"+resp_rsp2[7:]
                    sock.send(resp_rsp2)
                    data = sock.recv(MTU)
                    new_ch = conn_rsp[5]
                    sock.send(bytes(UA.gen(transition=True, channel=new_ch>>1, dir=new_ch&0b1)))
                    print(f"[*] new channel{conn_rsp[5]>>1} connection ")
                    is_new_chan = True
                    sock.send(UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=new_ch>>1, transition=True, mx_type=MSC, dir=new_ch&0b1))
                    try:
                        while True:
                            conn_rsp, sock = inter_recv(sock)
                            print(conn_rsp[3] == 0xe1)
                            if conn_rsp[3] == 0xe3:
                                sock.send(b'\x03' + conn_rsp[1:3]+b"\xe1"+conn_rsp[4:-1]+b"\xaa")
                            elif conn_rsp[3] == 0xe1:
                                print("[*] is here??")
                                sock.send(DATA.gen(transition=True, channel=new_ch>>1, dir=new_ch&0b1))
                                break
                    except:
                        print("[-] no msc")
                    break
                
                else:
                    print(conn_rsp)
                    break
        except:
            print("[-] no additional ch open")
        
        if is_new_chan:
            return sock, new_ch>>1, new_ch&0b1
        else:
            return sock, False, None
    else:
        return False


def open_channel(channel, target_addr):
    global ctrl_current_state
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))

    if not sock:
        print("[!] cannot create socket")
        return False

    if channel == CTRL_CHANNEL:
        sock.send(SABM.gen(channel=CTRL_CHANNEL, transition=True))
        
        conn_rsp, sock = inter_recv(sock)
        if conn_rsp == None:
            print('[*] recv failed.')
            return False
        else:  
            frame_pkt = FRAME_PKT(conn_rsp)
            res = frame_pkt.parse_pkt()
            if res:
                if res != "UA":
                    print(f"[*] cannot open channel{channel}")
                    return False
            ctrl_current_state = OPENED_CTRL_CH

    else:
        # enable ctrl channel
        sock.send(SABM.gen(channel=CTRL_CHANNEL, transition=True))
        
        conn_rsp, sock = inter_recv(sock)
        if conn_rsp == None:
            print('[*] recv failed.')
            return False
        else:  
            frame_pkt = FRAME_PKT(conn_rsp)
            res = frame_pkt.parse_pkt()
            if res:
                if res != "UA":
                    print(f"[*] cannot open channel{channel}")
                    return False
            ctrl_current_state = OPENED_CTRL_CH
        #sock.send(DISC.gen(channel=channel, transition=True))
        sock.send(UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel, transition=True, mx_type=PN))
        sleep(0.1)
        conn_rsp, sock = inter_recv(sock)
        sock.send(SABM.gen(channel=channel, transition=True))
        sleep(0.1)
        try:
            conn_rsp, sock = inter_recv(sock)
        except:
            print(f"[*] cannot open channel{channel}")
            return False
        frame_pkt = FRAME_PKT(conn_rsp)
        res = frame_pkt.parse_pkt()
        if res:
            if res != "UA":
                print(f"[*] cannot open channel{channel}")
                return False

        try:    
            while True:
                conn_rsp, sock = inter_recv(sock)
                if conn_rsp[3] == 0xe3 or conn_rsp[3] == 0xe1:
                    break
        except:
            print("NO MSC")
            return sock
        try:
            conn_rsp2, sock = inter_recv(sock)
        except:
            print("No credits")
        print("MSC state")            
        sock.send(b'\x03' + conn_rsp[1:])
        conn_rsp, sock = inter_recv(sock)
        print(conn_rsp.hex())
        sock.send(b'\x03' + conn_rsp[1:])
        try:
            conn_rsp, sock = inter_recv(sock)
            print("MSC done, w response")
        except:
            print("MSC done, no response")
    return sock


    




