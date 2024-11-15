import random
import bluetooth

from layer.rfcomm.const import RFCOMM_PSM
from layer.rfcomm.types.dm import DM
from layer.rfcomm.types.disc import DISC
from layer.rfcomm.types.sabm import SABM
from layer.rfcomm.types.ua import UA
from layer.rfcomm.types.uih import UIH

TYPES = [
    DM,
    DISC,
    SABM,
    UA,
    UIH
]

class RFCOMM:
    def mutate(self):
        type = random.choice(TYPES)
        control = type.gen()
        return bytes(control)
        
    def fuzz(self, bt_addr: bytes):
        cnt = 0
        while True:
            if cnt % 1000 == 0:
                print(f'fuzz count : {cnt}')
            sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
            sock.connect((bt_addr.decode(), RFCOMM_PSM))
            sock.send(self.mutate())
            cnt += 1
            sock.close()