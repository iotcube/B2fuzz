from datetime import datetime
from pprint import pprint
#from modules import *
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

# Base state in RFCOMM
CLOSED = 0
OPENED_CTRL_CH = 1
CLOSED_NORMAL_CH = 2
OPENED_NORMAL_CH = 3
OPENED_NORMAL_CH_WITH_MSC = 4

# Control channel(DLCI = 0)
CTRL_CHANNEL = 0

# RFCOMM frame and command set
RFCOMM_FRAME = [DM, DISC, SABM, UA, UIH, DATA]
RFCOMM_CMD = [FCON, FCOFF, INVALID, MSC, NSC, PN, RLS, RPN, TEST]

# new state counter
new_state = 5

def closed(target_addr, ch=0):
    """
    Establish L2CAP connection with pybluez module.\n
    This is initial state if RFCOMM.
    
    Parameters
    ----------
     - target_addr: [string] target device's MAC address

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - bluetooth socket (if connection is successful)
     - False (cannot connect to target)
    """
    # [1] Make bluetooth socket via pybluez 
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    try:
    # [2] connect RFCOMM session
        sock.connect((target_addr, RFCOMM_PSM))
    except Exception as e:
        print(e)
    # [3] if connection is not succesful, return False
        sock.close()
        return False
    # [4] retuen RFCOMM socket
    return sock

def opened_ctrl_ch(target_addr, ch=0):
    """
    Return RFCOMM socket with opening control channel (DLCI=0)
    
    RFCOMM/DEVA/RFC/BV-01-C test suit senario
    
    Parameters
    ----------
     - target_addr: [string] target device's MAC address

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - bluetooth socket (if connection is successful)
     - False (cannot connect to target)
    """

    # [1] Make RFCOMM session to target device
    sock = closed(target_addr)
    if not sock:
        return False
    
    # [2] Send SABM frame. This is request for opening control channel
    sock.send(SABM.gen(channel=CTRL_CHANNEL, transition=True))
    
    # [3] Recieve UA frame. If recieved frame is not UA(accept), return False. 
    try:
        conn_rsp, sock = inter_recv(sock)
    except:
        sock.close()
        return False
    if conn_rsp == None or conn_rsp == b"":
        print('[*] recv failed.')
        sock.close()
        return False
    else:  
        frame_pkt = FRAME_PKT(conn_rsp)
        res = frame_pkt.parse_pkt()
        if res:
            if res != "UA":
                print(f"[*] cannot open channel0")
                sock.close()
                return False
    return sock

def closed_normal_ch(target_addr, channel):
    """
    Return RFCOMM socket with parameter negotiation(PN) for target channel(DLCI)
    
    RFCOMM/DEVA/RFC/BV-05-C test suit senario
    
    Parameters
    ----------
     - target_addr: [string] target device's MAC address
     - channel: [int] target profile port(DLCI)

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - bluetooth socket (if connection is successful)
     - False (cannot connect to target)
    """

    # [1] Open control channel
    sock = opened_ctrl_ch(target_addr)
    if not sock:
         return False
    
    # [2] Send PN packet to target profile DLCI
    sock.send(UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel, transition=True, mx_type=PN))
    try:
    # [3] Recieve response frame for sended PN frame
        while True:
            conn_rsp, sock = inter_recv(sock)
            frame_pkt = FRAME_PKT(conn_rsp)
            res = frame_pkt.parse_pkt()
            if res:
                if res == "UIH":
                    break
                else:
                    print(f"[*] cannot open channel{channel}")
                    sock.close()
                    return False
    except:
        print(f"[*] cannot open channel{channel}")
        sock.close()
        return False

    return sock 


def establish_dlci(sock, channel):
    """
    Establish target profile DLCI channel with SABM, UA exchange.
    
    RFCOMM/DEVA/RFC/BV-05-C test suit senario
    
    Parameters
    ----------
     - sock: bluetooth socket after PN negotiation. (CLOSED_NORMAL_CH state)
     - channel: [int] target profile port(DLCI)

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - bluetooth socket (if connection is successful)
     - False (cannot connect to target)
    """

    # [1] Send SABM frame to target profile DLCI. 
    sock.send(SABM.gen(channel=channel, transition=True))
    # [2] Recieve UA frame. If recieved frame is not UA(accept), return False. 
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
                    sock.close()
                    return False
    except:
        print(f"[*] cannot open channel{channel}")
        sock.close()
        return False

    return sock 

def open_normal_ch(target_addr, channel):
    """
    Establish target profile DLCI channel with SABM, UA exchange.
    
    RFCOMM/DEVA/RFC/BV-05-C test suit senario
    
    Difference to `establish_dlci` is first parameter

    Parameters
    ----------
     - target_addr: [string] target device MAC address
     - channel: [int] target profile port(DLCI)

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - bluetooth socket (if connection is successful)
     - False (cannot connect to target)
    """
    # [1] Make RFCOMM socket with CLOSED_NORMAL_CH state. (parameter negotiation)
    sock= closed_normal_ch(target_addr, channel)
    if sock:
    
    # [2] Request for opening target profile DLCI.
        sock = establish_dlci(sock, channel)
    return sock

def open_normal_ch_with_msc(target_addr, channel):
    """
    Make RFCOMM session wirh MSC command exchange.

    After running this function. RFCOMM socket is ready to send/recieve profile data.
    
    RFCOMM/DEVA-DEVB/RFC/BV-22-C test suit senario
    

    Parameters
    ----------
     - target_addr: [string] target device MAC address
     - channel: [int] target profile port(DLCI)

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - bluetooth socket (if connection is successful)
     - False (cannot connect to target)
    """

    # [1] Make RFCOMM socket with CLOSED_NORMAL_CH state. (parameter negotiation)
    sock= closed_normal_ch(target_addr, channel)
    if sock:
    # [2] Request for opening target profile DLCI.
        sock = establish_dlci(sock, channel)

    # [3] Make MSC command exchange. 
        return new_chan_msc(sock, channel, 0)
    else:
        return False, False

def open_new_chan(target_addr, channel):
    """
    Test if there is another PN request from target.
    
    This situation is observed redmi buds pro.

    Parameters
    ----------
     - target_addr: [string] target device MAC address
     - channel: [int] target profile port(DLCI)

    Raises
    ----------
     - bluetooth error

    Returns
    ----------
     - [tuple] (bluetooth socket, new_channel DLCI) : if there is new PN request form target
     - (False, False) : else
    """

    # [1] Make DLCI connection with target profile
    sock, _ = open_normal_ch_with_msc(target_addr, channel)
    is_new_chan = False

    # [2] Wait another PN request
    try:
        while True:
            conn_rsp, sock = inter_recv(sock)

    # [3] If there is another PN requset. respond it.
            if conn_rsp[3] == 0x83: 
                # [3-1] Response is just to change direction bit in control field.
                resp_rsp2 = b'\x03' + conn_rsp[1:]
                resp_rsp2 = resp_rsp2[:3]+b"\x81"+resp_rsp2[4:]
                resp_rsp2 = resp_rsp2[:6]+b"\xe0"+resp_rsp2[7:]
                sock.send(resp_rsp2)
                new_ch = conn_rsp[5]
                is_new_chan = True
                break
    except:
        print("[*] no additional state")
    # [4] Return new channel DLCI and socket
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
                pkt = b'\x03' + conn_rsp[1:3]+b"\xe1"+conn_rsp[4:-1]
                sock.send(pkt + bytes([calc_fcs(2, pkt)]))
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

