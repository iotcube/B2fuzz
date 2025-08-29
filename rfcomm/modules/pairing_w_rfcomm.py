from datetime import datetime
from pprint import pprint
from modules import *
from lib import *
from time import sleep
import random
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

def gen_random_data(len):
    return b''.join(random.choices([bytes([x]) for x in range(0x00, 0x100)], k=len))

def open_rfcomm_channel(channel, target_addr):
    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

    sock.connect((target_addr, channel))

    print("[-] send pkt")
    sock.send(b"\r\nAT+"+gen_random_data(100)+b"\r\n")
    try:
        res = sock.recv(MTU)
    except:
        print("[-] no res")
        return False
    print(f"[-] response: {res}")
    #sock.close()
