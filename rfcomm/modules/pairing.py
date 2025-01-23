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
CLOSED_NORMAL_CH = 2
OPENED_NORMAL_CH = 3
OPENED_NORMAL_CH_WITH_MSC = 4


CTRL_CHANNEL = 0

RFCOMM_FRAME = [DM, DISC, SABM, UA, UIH, DATA]

new_state = 5

def closed(target_addr):
    global ctrl_current_state
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    sock.connect((target_addr, RFCOMM_PSM))
    return sock

def opened_ctrl_ch(target_addr):
    sock = closed(target_addr)
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
def closed_normal_ch(target_addr, channel):
    # enable ctrl channel
    sock = opened_ctrl_ch(target_addr)
    sock.send(UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel, transition=True, mx_type=PN))
    try:
        while True:
            conn_rsp, sock = inter_recv(sock)
            frame_pkt = FRAME_PKT(conn_rsp)
            res = frame_pkt.parse_pkt()
            if res:
                if res == "UIH":
                    break
                else:
                    print(f"[*] cannot open channel{channel}")
                    return False
    except:
        print(f"[*] cannot open channel{channel}")
        return False

    return sock 


def establish_dlci(sock, channel):
    sock.send(SABM.gen(channel=channel, transition=True))
    try:
        while True:
            conn_rsp, sock = inter_recv(sock)
            frame_pkt = FRAME_PKT(conn_rsp)
            res = frame_pkt.parse_pkt()
            if res:
                if res == "UA":
                    break
                else:
                    print(f"[*] cannot open channel{channel}")
                    return False
    except:
        print(f"[*] cannot open channel{channel}")
        return False

    return sock 

def open_normal_ch_with_msc(target_addr, channel):
    sock= closed_normal_ch(target_addr, channel)
    sock = establish_dlci(sock, channel)
    if sock:
        return new_chan_msc(sock, channel, 0)
    else:
        return False, False

def open_new_chan(target_addr, channel):
    sock, _ = open_normal_ch_with_msc(target_addr, channel)
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
                new_ch = conn_rsp[5]
                is_new_chan = True
                break
    except:
        print("[*] no additional state")

    if is_new_chan:
        return sock, new_ch
    else:
        return False, False

def establish_new_dlci(sock, new_ch):
    try:
        while True:
            conn_rsp, sock = inter_recv(sock)
            frame_pkt = FRAME_PKT(conn_rsp)
            res = frame_pkt.parse_pkt()
            if res:
                if res == "SABM":
                    sock.send(UA.gen(transition=True, channel=new_ch>>1, dir=new_ch&0b1))
                    break
                else:
                    print(f"[*] cannot open channel{new_ch}")
                    return False
            
    except:
        print(f"[*] cannot open channel{new_ch}")
        return False

    return sock 


def new_chan_msc(sock, channel, dir):
    sock.send(UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel, transition=True, mx_type=MSC, dir=dir))
    is_msc = False    
    try:
        while True:
            conn_rsp, sock = inter_recv(sock)
            if conn_rsp[3] == 0xe3:
                sock.send(b'\x03' + conn_rsp[1:3]+b"\xe1"+conn_rsp[4:-1]+b"\xaa")
                is_msc = True
            elif conn_rsp[3] == 0xe1:
                break
    except:
        pass
    # Credite
    sock.send(DATA.gen(transition=True, channel=channel, dir=dir))
    return sock, is_msc

def find_state(sock):
    is_new_state = False
    try:
        while True:
            conn_rsp, sock = inter_recv(sock)
            frame_pkt = FRAME_PKT(conn_rsp)
            res = frame_pkt.parse_pkt()
            if conn_rsp[3] != 0x83 and res and (res != "DM" and res != "DISC"):
                is_new_state = True
                break
    except:
        print("[-] no additional state")
    return is_new_state

