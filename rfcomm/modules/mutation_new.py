import random
import traceback
import sys
import time
from collections import OrderedDict
from datetime import date, datetime
from modules.logger import *
from modules.construct_sm import *
from modules.pairing import *
from lib import *

now = datetime.now()
t = str(now)[11:19].replace(':',"",2)
today = date.today()
today = today.isoformat()
d = today[2:4] + today[5:7] + today[8:10]

def get_logtime():
    global d
    global t
    return d+t
logger = Logger(get_logtime())
tmp = 0
crash_cnt = 0
pkt_cnt = 0

MUTATION_CNT = 200

def _pf(const):
    return const | (1 << 4)

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

def parse_pkt(pkt):
    payload = {}
    payload['Address'] = hex(pkt[0])
    payload['Control'] = {
        'frame type': hex(_pf(pkt[1]))
    }
    payload['length'] = ((pkt[2] - 1) << 1)
    payload['data'] = pkt[3:-1].hex()
    payload['fcs'] = hex(pkt[-1])
    return payload

def fuz_send_pkt(bt_addr, sock, pkt, state, channel_to_ctrl=0):
    """
    Errno
        ConnectionResetError: [Errno 104] Connection reset by peer
        ConnectionRefusedError: [Errno 111] Connection refused
        TimeoutError: [Errno 110] Connection timed out 
        and so on ..
    """
    global crash_cnt
    global pkt_cnt
    global tmp_pkt
    pkt_info = ""
    pkt_cnt += 1
    is_crashed = False
    try:
        if pkt not in RFCOMM_CMD:
            tmp_pkt = pkt.gen(channel=channel_to_ctrl)
            sock.send(tmp_pkt)
        else:
            tmp_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel_to_ctrl, transition=False, mx_type=pkt)
            sock.send(tmp_pkt)
        pkt_info = {}
        pkt_info['no'] = pkt_cnt
        pkt_info['protocol'] = 'RFCOMM'
        pkt_info['sended_time'] = str(datetime.now())
        pkt_info['payload'] = parse_pkt(tmp_pkt)
        pkt_info['crash'] = 'n'
        pkt_info['state'] = state2str(state)

    except ConnectionResetError:
        print("[-] Crash Found - ConnectionResetError detected")
        if(l2ping(bt_addr) == False):
            print("Crash Packet :", tmp_pkt)
            crash_cnt += 1
            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(tmp_pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "ConnectionResetError"
            is_crashed = True

    except bluetooth.BluetoothError as e:
        print(f"[-] Crash Found - {e} detected")
        print("Crash Packet :", tmp_pkt)
        crash_cnt += 1

        logger.Q_crash_cnt += 1
        print("Crash packet count : ", crash_cnt)
        pkt_info = {}
        pkt_info["no"] = pkt_cnt
        pkt_info["protocol"] = "RFCOMM"
        pkt_info["sended_time"] = str(datetime.now())
        pkt_info["payload"] = parse_pkt(tmp_pkt)
        pkt_info["state"] = state2str(state)
        pkt_info["sended?"] = "n"			
        pkt_info["crash"] = "y"
        pkt_info["crash_info"] = f"{e}"
        is_crashed = True
        
    else: pass

    time.sleep(0.1)
    if(pkt_info == ""): pass
    else: logger.inputQueue(pkt_info)
    return is_crashed

def closed_state_fuzzing(target_addr, state_frame, ch=0):
    print("[-] current state: closed")
    global tmp_pkt
    global crash_cnt
    for _ in range(MUTATION_CNT): 
        sock = closed(target_addr)
        if sock:
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[CTRL_CHANNEL][CLOSED]), CLOSED)
            sock.close()
        else:
            print(f"[-] Crash Found - State violation detected")
            print("Crash Packet :", tmp_pkt)
            crash_cnt += 1

            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(tmp_pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "State violation"
            is_crashed = True
            if(pkt_info == ""): pass
            else: logger.inputQueue(pkt_info)
            break
    time.sleep(0.1)
    return is_crashed

def open_ctrl_ch_state_fuzzing(target_addr, state_frame, ch=0):
    print("[-] current state: open_ctrl_ch")
    for _ in range(MUTATION_CNT): 
        sock = opened_ctrl_ch(target_addr)
        if sock:
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[CTRL_CHANNEL][OPENED_CTRL_CH]), OPENED_CTRL_CH)
            sock.close()
        else:
            print(f"[-] Crash Found - State violation detected")
            print("Crash Packet :", tmp_pkt)
            crash_cnt += 1

            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(tmp_pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "State violation"
            is_crashed = True
            if(pkt_info == ""): pass
            else: logger.inputQueue(pkt_info)
            break
    time.sleep(0.1)
    return is_crashed

def closed_normal_ch_state_fuzzing(target_addr, state_frame, ch):
    print("[-] current state: closed_normal_ch")
    global tmp_pkt
    global crash_cnt
    for _ in range(MUTATION_CNT): 
        sock = closed_normal_ch(target_addr, ch)
        if sock:
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[ch][CLOSED_NORMAL_CH]), CLOSED_NORMAL_CH, channel_to_ctrl=ch)
            sock.close()
        else:
            print(f"[-] Crash Found - State violation detected")
            print("Crash Packet :", tmp_pkt)
            crash_cnt += 1

            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(tmp_pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "State violation"
            is_crashed = True
            if(pkt_info == ""): pass
            else: logger.inputQueue(pkt_info)
            break
    time.sleep(0.1)
    return is_crashed

def opened_normal_ch_state_fuzzing(target_addr, state_frame, ch):
    print("[-] current state: opened_normal_ch")
    global tmp_pkt
    global crash_cnt
    for _ in range(MUTATION_CNT): 
        sock = open_normal_ch(target_addr, ch)
        if sock:
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[ch][OPENED_NORMAL_CH]), OPENED_NORMAL_CH, channel_to_ctrl=ch)
            sock.close()
         
        else:
            print(f"[-] Crash Found - State violation detected")
            print("Crash Packet :", tmp_pkt)
            crash_cnt += 1

            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(tmp_pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "State violation"
            is_crashed = True
            if(pkt_info == ""): pass
            else: logger.inputQueue(pkt_info)
            break
    time.sleep(0.1)
    return is_crashed


def opened_normal_ch_with_msc_state_fuzzing(target_addr, state_frame, ch):
    print("[-] current state: opened_normal_ch_with_msc")
    global tmp_pkt
    global crash_cnt
    for _ in range(MUTATION_CNT): 
        sock, _ = open_normal_ch_with_msc(target_addr, ch)
        if sock:
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[ch][OPENED_NORMAL_CH_WITH_MSC]), OPENED_NORMAL_CH_WITH_MSC, channel_to_ctrl=ch)
            sock.close()
        else:
            print(f"[-] Crash Found - State violation detected")
            print("Crash Packet :", tmp_pkt)
            crash_cnt += 1

            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(tmp_pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "State violation"
            is_crashed = True
            if(pkt_info == ""): pass
            else: logger.inputQueue(pkt_info)
            break
    time.sleep(0.1)
    return is_crashed

def new_state_fuzzing(target_addr, state_frame, ch, state, path):
    print(f"[-] current state: new_state{state - 4}")
    global tmp_pkt
    global crash_cnt
    for _ in range(MUTATION_CNT):
        if path[state - 5][0] == open_normal_ch_with_msc:
            sock, _ = open_normal_ch_with_msc(target_addr, ch)
        else:
            sock = path[state - 5][0](target_addr, ch)
        if sock:
            sock.send(path[state - 5][1].gen(channel=ch))
        else:
            sock = False
        if sock:
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(RFCOMM_CMD + RFCOMM_FRAME), state, channel_to_ctrl=ch)
            sock.close()
        else:
            print(f"[-] Crash Found - State violation detected")
            print("Crash Packet :", tmp_pkt)
            crash_cnt += 1

            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(tmp_pkt)
            pkt_info["state"] = state2str(state)+" "+(str(path[state - 5][0]).split())[1]+" "+str(path[state - 5][1])
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "State violation"
            is_crashed = True
            if(pkt_info == ""): pass
            else: logger.inputQueue(pkt_info)
            break
    time.sleep(0.1)
    return is_crashed

def mutation_in_normal_state(target_addr, sm, path):
    for channel in sm:
        for state in sm[channel]:
            if state == CLOSED:
                is_crashed = closed_state_fuzzing(target_addr, sm)
                if is_crashed: return True
            elif state == OPENED_CTRL_CH:
                is_crashed = open_ctrl_ch_state_fuzzing(target_addr, sm)
                if is_crashed: return True
            elif state == CLOSED_NORMAL_CH:
                is_crashed = closed_normal_ch_state_fuzzing(target_addr, sm, channel)
                if is_crashed: return True
            elif state == OPENED_NORMAL_CH:
                is_crashed = opened_normal_ch_state_fuzzing(target_addr, sm, channel)
                if is_crashed: return True
            elif state == OPENED_NORMAL_CH_WITH_MSC:
                is_crashed = opened_normal_ch_with_msc_state_fuzzing(target_addr, sm, channel)
                if is_crashed: return True
            if state >= 5:
                is_crashed = new_state_fuzzing(target_addr, sm, channel, state, path)
                if is_crashed: return True
            else:
                pass
                




def logsave(loggerDict):
    loggerDict["end_time"] = str(datetime.now())
    loggerDict["count"] = {"all" : pkt_cnt, "crash" : crash_cnt, "passed" : pkt_cnt-crash_cnt}
    logger.inputQueue(loggerDict)
    logger.logUpdate()
    logger.init_info(loggerDict)

def fuzzing(target_addr, profile, port, adaptive_state_frame, test_info, path):
    global tmp
    global crash_cnt
    now = datetime.now()
    tmp = 0
    test_info["starting_time"] = str(now)
    logger.init_info(test_info)
    if(profile == "None" or port == "None"):
        print('Cannot Fuzzing')
        return
    print("Start Fuzzing... Please hit Ctrl + C to finish...")

    logger.start = time.time()
    try:
        while True:
            print("[+] Tested %d packets" % (pkt_cnt))
            loggerDict = {}
            #is_crashed = False
            is_crashed = mutation_in_normal_state(target_addr, adaptive_state_frame, path)
            if is_crashed:
                break
            #is_crashed = mutation_in_adaptive_state(target_addr, adaptive_state_frame)
            #if is_crashed:
            #    break
            logger.inputQueue("**ITEREND**")
            print("********************************************************************")
            logger.end = time.time()
            if logger.end - logger.start > 60:
                logger.start = time.time()
                t1 = threading.Thread(target=logger.logUpdate())
                t1.start()

            if pkt_cnt > 2000000:
                print('[*] Save logfile')
                print('iteration END@@@@@@@@@@')
                logsave(loggerDict)
                break

        if is_crashed:
            print('[*] Save logfile')
            print("iteration END@@@@@@@@@")
            logger.inputQueue('**ITEREND**')
            logsave(loggerDict)

    except Exception as e:
        print("[!] Error Message :", e, traceback.format_exc())
        print("[+] Save logfile")
        loggerDict["count"] = {"all" : pkt_cnt, "crash" : crash_cnt, "passed" : pkt_cnt-crash_cnt}
        logsave(loggerDict)
    
    except KeyboardInterrupt as k:
        print("[!] Fuzzing Stopped :", k, traceback.format_exc())
        print("[+] Save logfile")
        loggerDict["end_time"] = str(datetime.now())
        loggerDict["count"] = {"all" : pkt_cnt, "crash" : crash_cnt, "passed" : pkt_cnt-crash_cnt}
        print("[*] Assign queue update for key interrupt to thread")
        logsave(loggerDict)

    print(f"Total pkt cnt: {pkt_cnt}, crashcnt : {crash_cnt}")