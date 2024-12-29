import pathlib
import pprint
import json
import bluetooth
from const import DEBUG_STR
from layer.parser import Parser
from layer.rfcomm.modules import *
from layer.sender import Sender


class RFCOMMParser(Parser):
    def __init__(self, filepath: pathlib.Path):
        self.filepath: pathlib.Path = filepath
        self.info_end_idx: int = 0
        self.get_raw_text()
        self.wfl = {}

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
        self.info = json.loads(ret)

        with open(self.filepath.parent / 'info.wfl', mode='w', encoding='utf-8') as f:
            f.write(ret)
        self.wfl["info"] = self.info

        self.info_end_idx = info_end_idx

    def get_pkts(self):
        self.raw_text_lines[self.info_end_idx] = self.raw_text_lines[self.info_end_idx]
        self.pkts = self.raw_text_lines[self.info_end_idx:]
        for idx, line in enumerate(self.pkts):
            if DEBUG_STR in self.pkts[idx]:
                self.pkts[idx] = line.replace(DEBUG_STR, '').replace('\'', '"')
        self.packets_pkts = {"packets": []}
        for pkt in self.pkts:
            if 'end_time' in pkt:
                break
            if '**ITEREND**' in pkt:
                continue
            self.packets_pkts["packets"].append(json.loads(pkt.replace("None", "null"))) 

        with open(self.filepath.parent / 'packets.wfl', mode='w', encoding='utf-8') as f:
            json_str = pprint.pformat(self.packets_pkts, compact=True).replace('\'', '"').replace("None", "null")
            f.write(json_str)
        file_name = str(self.filepath.parent).split('/')[-1] + '.wfl'
        self.wfl["pkt"] = self.packets_pkts["packets"]
        with open(self.filepath.parent / file_name, mode='w', encoding='utf-8') as f:
            json.dump(self.wfl, f)

class RFCOMMSender(Sender):
    def __init__(self, bt_addr):
        self.bt_addr = bt_addr
        self.total_crashcnt: int = 0
        self.total_sended_pktcnt: int = 0
    
    def connect(self):
        self.sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
        self.sock.connect((self.bt_addr, RFCOMM_PSM))
        
    def dict2pkt(self, dict_pkt: dict):
        payload = bytearray(5)
        payload[0] = int(dict_pkt['Address'], 16)
        payload[1] = int(dict_pkt['Control']['frame type'], 16)
        payload[2] = (dict_pkt['length'] >> 1) + 1
        payload[3:-1] = bytes.fromhex(dict_pkt['data'])
        payload[-1] = int(dict_pkt['fcs'], 16)
        return payload
    
    def run(self, packets_json):
        self.connect()
        with open(packets_json, mode='r', encoding='utf-8') as f:
            iterlist = json.load(f)

        pkts = iterlist["packets"]
        for pkt in pkts:
            pkt_send_cnt = 0
            is_resend_required = False
            while True:
                crashcnt, is_resend_required = fuz_send_pkt(self.bt_addr, self.sock, self.dict2pkt(pkt["payload"]), pkt["state"])
                self.total_crashcnt += crashcnt
                self.total_sended_pktcnt += 1
                pkt_send_cnt += 1
                if pkt_send_cnt >= 3 or not is_resend_required:
                    break
                print(f"Try {pkt_send_cnt} send, " + f"fail? : {is_resend_required}")
                exit(1)
            print("***Total Crash Count : ", self.total_crashcnt)
            print("***Total Sended Packet Count : ", self.total_sended_pktcnt)