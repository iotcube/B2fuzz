import pathlib
import pprint
import json
import datetime
from const import DEBUG_STR
from layer.parser import Parser
from layer.l2cap.module.btpkt import *
from layer.l2cap.module.detect import * 
from layer.sender import Sender
from scapy.layers.bluetooth import BluetoothL2CAPSocket
crash_cnt = 0
pkt_cnt = 0
def bin_send_pkt(bt_addr, sock, pkt, cmd_code, state):
    """
    Errno
        ConnectionResetError: [Errno 104] Connection reset by peer
        ConnectionRefusedError: [Errno 111] Connection refused
        TimeoutError: [Errno 110] Connection timed out 
        and so on ..
    """
    global crash_cnt
    global pkt_cnt
    tmp_crash_cnt = 0
    pkt_cnt += 1
    pkt_info = ""
    is_resend_required = False

    try:
        sock.send(pkt)
        pkt_info = {}
        pkt_info["no"] = pkt_cnt
        pkt_info["protocol"] = "L2CAP"
        pkt_info["sended_time"] = str(datetime.now())
        pkt_info["payload"] = log_pkt(pkt)
        pkt_info["crash"] = "n"
        pkt_info["l2cap_state"] = state

    except ConnectionResetError:
        print("[-] Crash Found - ConnectionResetError detected")
        if(l2ping(bt_addr) == False):
            print("Crash Packet :", pkt)
            crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "L2CAP"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["cmd"] = cmd_code
            pkt_info["payload"] = log_pkt(pkt)
            pkt_info["l2cap_state"] = state
            pkt_info["sended?"] = "n"
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "ConnectionResetError"
            print("Crash Packet :", pkt_info)
            tmp_crash_cnt += 1
        else:
            is_resend_required = True

    except ConnectionRefusedError:
        print("[-] Crash Found - ConnectionRefusedError detected")
        if(l2ping(bt_addr) == False):
            print("Crash Packet :", pkt)
            crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "L2CAP"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["cmd"] = cmd_code
            pkt_info["payload"] = log_pkt(pkt)
            pkt_info["l2cap_state"] = state			
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "ConnectionRefusedError"
            print("Crash Packet :", pkt_info)
            tmp_crash_cnt += 1
        else:
            is_resend_required = True
    except ConnectionAbortedError:
        print("[-] Crash Found - ConnectionAbortedError detected")
        if(l2ping(bt_addr) == False):
            print("Crash Packet :", pkt)
            crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "L2CAP"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["cmd"] = cmd_code
            pkt_info["payload"] = log_pkt(pkt)
            pkt_info["l2cap_state"] = state			
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "ConnectionAbortedError"
            print("Crash Packet :", pkt_info)
            tmp_crash_cnt += 1
        else:
            is_resend_required = True
    except TimeoutError:
        # State Timeout
        print("[-] Crash Found - TimeoutError detected")
        crash_cnt += 1
        print("Crash packet count : ", crash_cnt)
        pkt_info = {}
        pkt_info["no"] = pkt_cnt
        pkt_info["protocol"] = "L2CAP"
        pkt_info["sended_time"] = str(datetime.now())
        pkt_info["cmd"] = cmd_code
        pkt_info["payload"] = log_pkt(pkt)
        pkt_info["l2cap_state"] = state
        pkt_info["sended?"] = "n"			
        pkt_info["crash"] = "y"
        pkt_info["crash_info"] = "TimeoutError"
        print("Crash Packet :", pkt_info)
        tmp_crash_cnt += 1

    except OSError as e:
        """
        OSError: [Errno 107] Transport endpoint is not connected
        OSError: [Errno 112] Host is down
        """
        if "Host is down" in e.__doc__:
            print("[-] Crash Found - Host is down")
            print("Crash Packet :", pkt)
            crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "L2CAP"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["cmd"] = cmd_code
            pkt_info["payload"] = log_pkt(pkt)
            pkt_info["l2cap_state"] = state
            pkt_info["sended?"] = "n"
            pkt_info["crash"] = "y"
            pkt_info["DoS"] = "y"
            pkt_info["crash_info"] = "OSError - Host is down"
            tmp_crash_cnt += 1
            print("[-] Crash packet causes HOST DOWN. Test finished.")
            print(pkt_info)
        else:
            is_resend_required = True

    except Exception as e:
        print(f"Undefined Error detected : {e}")
        print("[-] Crash Found - Undefined Error detected")
        if(l2ping(bt_addr) == False):
            crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "L2CAP"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["cmd"] = cmd_code
            pkt_info["payload"] = log_pkt(pkt)
            pkt_info["l2cap_state"] = state
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "Undefined Error"
            print("Crash Packet :", pkt_info)
            tmp_crash_cnt += 1
        else:
            is_resend_required = True
	# Reset Socket
    try:
        sock = BluetoothL2CAPSocket(bt_addr)
    except:
        pass
    return sock, tmp_crash_cnt, is_resend_required


def replay_make_btpkt(sock, packet):
    global check_flag
    global con_dcid

    cmd_code = packet["payload"]["code"]

    p_dcid = 0
    if "dcid" in packet["payload"].keys():
        p_dcid = packet["payload"]["dcid"]

    p_garbage = 0
    if "garbage" in packet["payload"].keys():
        p_garbage = packet["payload"]["garbage"]

    if cmd_code in [L2CAP_CMD_CONN_REQ, L2CAP_CMD_CREATE_CHANNEL_REQ]:
        p_psm = packet["payload"]["psm"]
        if cmd_code == L2CAP_CMD_CONN_REQ:
            pkt = L2CAP_CmdHdr(code=cmd_code)/new_L2CAP_ConnReq(psm=p_psm)/garbage_value(garbage=p_garbage)
        else:
            pkt = L2CAP_CmdHdr(code=cmd_code)/L2CAP_Create_Channel_Request(psm=p_psm)/garbage_value(garbage=p_garbage)
    elif cmd_code in [L2CAP_CMD_CONN_RSP, L2CAP_CMD_DISCONN_REQ, L2CAP_CMD_CREATE_CHANNEL_RSP]:
        p_scid = packet["payload"]["scid"]
        if cmd_code == L2CAP_CMD_CONN_RSP:
            pkt = L2CAP_CmdHdr(code=cmd_code)/new_L2CAP_ConnResp(dcid=p_dcid, scid=p_scid)/garbage_value(garbage=p_garbage)
        elif cmd_code == L2CAP_CMD_DISCONN_REQ:
            pkt = L2CAP_CmdHdr(code=cmd_code)/L2CAP_DisconnReq(scid=p_scid, dcid=p_dcid)/garbage_value(garbage=p_garbage)
        else:
            pkt = L2CAP_CmdHdr(code=cmd_code)/L2CAP_Create_Channel_Response(scid=p_scid, dcid=p_dcid)/garbage_value(garbage=p_garbage)
    elif cmd_code in [L2CAP_CMD_CONFIG_REQ, L2CAP_CMD_CONFIG_RSP]:
        if cmd_code == L2CAP_CMD_CONFIG_REQ:
            pkt = L2CAP_CmdHdr(code=cmd_code)/new_L2CAP_ConfReq(dcid=p_dcid)/garbage_value(garbage=p_garbage)
        else:
            p_scid = packet["payload"]["scid"]
            pkt = L2CAP_CmdHdr(code=cmd_code)/new_L2CAP_ConfResp(scid=p_scid)/garbage_value(garbage=p_garbage)
    elif cmd_code in [L2CAP_CMD_MOVE_CHANNEL_RSP, L2CAP_CMD_MOVE_CHANNEL_CONFIRM_REQ, L2CAP_CMD_MOVE_CHANNEL_CONFIRM_RSP]:
        p_icid = packet["payload"]["icid"]
        if cmd_code == L2CAP_CMD_MOVE_CHANNEL_RSP:
            pkt = L2CAP_CmdHdr(code=cmd_code)/L2CAP_Move_Channel_Response(icid=p_icid)/garbage_value(garbage=p_garbage)
        elif cmd_code == L2CAP_CMD_MOVE_CHANNEL_CONFIRM_REQ:
            pkt = L2CAP_CmdHdr(code=cmd_code)/L2CAP_Move_Channel_Confirmation_Request(icid=p_icid)/garbage_value(garbage=p_garbage)
        else:
            pkt = L2CAP_CmdHdr(code=cmd_code)/L2CAP_Move_Channel_Confirmation_Response(icid=p_icid)/garbage_value(garbage=p_garbage)
    elif cmd_code == L2CAP_CMD_MOVE_CHANNEL_REQ:
        p_dest_controller_id = packet["payload"]["dest_controller_id"]
        pkt = L2CAP_CmdHdr(code=cmd_code)/L2CAP_Move_Channel_Request(dest_controller_id=p_dest_controller_id)/garbage_value(garbage=p_garbage)
    else:
        print("[cmd_code] : ", cmd_code)
        print("[packet no] : ", packet["no"])
        print("cmd code 가 범위 밖")
        sys.exit()

    return pkt, sock

class L2CAPParser(Parser):
    def __init__(self, filepath: pathlib.Path):
        self.filepath: pathlib.Path = filepath
        self.info_end_idx: int = 0
        self.get_raw_text()

    def get_info(self):
        self.raw_text_lines = [l for l in self.raw_text.split('\n')]
        info_start_idx, info_end_idx = 0, 0
        for i, line in enumerate(self.raw_text_lines):
            if DEBUG_STR not in line:
                info_start_idx = i
                break
        for i, line in enumerate(self.raw_text_lines[info_start_idx:]):
            if DEBUG_STR in line:
                info_end_idx = info_start_idx + i
                break

        ret = ''
        for l in self.raw_text_lines[info_start_idx:info_end_idx]:
            ret += (l+'\n')
        ret += '}'
        self.info = json.loads(ret)

        with open(self.filepath.parent / 'info.json', mode='w', encoding='utf-8') as f:
            f.write(ret)
        self.info_end_idx = info_end_idx

    def get_pkts(self):
        self.raw_text_lines[self.info_end_idx] = self.raw_text_lines[self.info_end_idx][1:]
        self.pkts = self.raw_text_lines[self.info_end_idx:]
        for idx, line in enumerate(self.pkts):
            if DEBUG_STR in self.pkts[idx]:
                self.pkts[idx] = line.replace(DEBUG_STR, '').replace('\'', '"')
        self.mini_range_pkts = {"0": {"packets": []}}
        for i, pkt in enumerate(self.pkts):
            if pkt == '**ITEREND**':
                continue
            if pkt == '':
                continue
            self.mini_range_pkts["0"]["packets"].append(json.loads(pkt.replace("None", "null")))  
        with open(self.filepath.parent / 'mini_range.json', mode='w', encoding='utf-8') as f:
            #json_str = pprint.pformat(self.mini_range_pkts, compact=True).replace('\'', '"').replace("None", "null"
            f.write(json.dumps(self.mini_range_pkts))


class L2CAPSender(Sender):
    def __init__(self, bt_addr):
        self.bt_addr = bt_addr
        self.total_crashcnt: int = 0
        self.total_sended_pktcnt: int = 0
        
    def connect(self):
        self.sock = BluetoothL2CAPSocket(self.bt_addr)
        
    def run(self, mini_range_json):
        self.connect()
        with open(mini_range_json, mode='r', encoding='utf-8') as f:
            iterlist = json.load(f)
        
        keys = list(iterlist.keys())
        print(f"[Total iteration] : {keys[0]}-{keys[-1]}") 

        for k in keys:
            pkts = iterlist[k]["packets"]
            print("{} target iteration ".format(k))
            for pkt in pkts:
                p, sock = replay_make_btpkt(self.sock, pkt)
                pkt_send_cnt = 0
                is_resend_required = False
                
                while True:
                    # send
                    sock, crashcnt, is_resend_required = bin_send_pkt(self.bt_addr, sock, p, pkt["payload"]["code"], pkt["l2cap_state"])
                    self.total_crashcnt += crashcnt
                    self.total_sended_pktcnt += 1
                    pkt_send_cnt += 1
                    if pkt_send_cnt >= 3 or not is_resend_required:
                        break
                    print(f"Try {pkt_send_cnt} send, "+ f"fail? : {is_resend_required}")
                    exit(1)
            print("***Total Crash Count : ", self.total_crashcnt)
            print("***Total Sended Packet Count : ", self.total_sended_pktcnt)