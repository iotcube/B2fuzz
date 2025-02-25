import random
import traceback
import sys
from collections import OrderedDict
from datetime import date, datetime
from modules.logger import *
from modules.construct_adaptive_sm import *
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

def fuz_send_pkt(bt_addr, sock, pkt, state):
    """
    Errno
        ConnectionResetError: [Errno 104] Connection reset by peer
        ConnectionRefusedError: [Errno 111] Connection refused
        TimeoutError: [Errno 110] Connection timed out 
        and so on ..
    """
    global crash_cnt
    global pkt_cnt
    pkt_info = ""
    pkt_cnt += 1
    is_crashed = False
    try:
        sock.send(pkt)
        pkt_info = {}
        pkt_info['no'] = pkt_cnt
        pkt_info['protocol'] = 'RFCOMM'
        pkt_info['sended_time'] = str(datetime.now())
        pkt_info['payload'] = parse_pkt(pkt)
        pkt_info['crash'] = 'n'
        pkt_info['state'] = state2str(state)

    except ConnectionResetError:
        print("[-] Crash Found - ConnectionResetError detected")
        if(l2ping(bt_addr) == False):
            print("Crash Packet :", pkt)
            crash_cnt += 1
            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "ConnectionResetError"
            is_crashed = True

    except ConnectionRefusedError:
        print("[-] Crash Found - ConnectionRefusedError detected")
        if(l2ping(bt_addr) == False):
            print("Crash Packet :", pkt)
            crash_cnt += 1

            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(pkt)	
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "ConnectionRefusedError"
            is_crashed = True

    except ConnectionAbortedError:
        print("[-] Crash Found - ConnectionAbortedError detected")
        if(l2ping(bt_addr) == False):
            print("Crash Packet :", pkt)
            crash_cnt += 1

            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "ConnectionAbortedError"		
            is_crashed = True

    except TimeoutError:
        # State Timeout
        print("[-] Crash Found - TimeoutError detected")
        print("Crash Packet :", pkt)
        crash_cnt += 1

        logger.Q_crash_cnt += 1
        print("Crash packet count : ", crash_cnt)
        pkt_info = {}
        pkt_info["no"] = pkt_cnt
        pkt_info["protocol"] = "RFCOMM"
        pkt_info["sended_time"] = str(datetime.now())
        pkt_info["payload"] = parse_pkt(pkt)
        pkt_info["state"] = state2str(state)
        pkt_info["sended?"] = "n"			
        pkt_info["crash"] = "y"
        pkt_info["crash_info"] = "TimeoutError"
        is_crashed = True

    except OSError as e:
        """
        OSError: [Errno 107] Transport endpoint is not connected
        OSError: [Errno 112] Host is down
        """
        if "Host is down" in e.__doc__:
            print("[-] Crash Found - Host is down")
            print("Crash Packet :", pkt)
            crash_cnt += 1
            
            logger.Q_crash_cnt += 1
            print("Crash packet count : ", crash_cnt)
            pkt_info = {}
            pkt_info["no"] = pkt_cnt
            pkt_info["protocol"] = "RFCOMM"
            pkt_info["sended_time"] = str(datetime.now())
            pkt_info["payload"] = parse_pkt(pkt)
            pkt_info["state"] = state2str(state)
            pkt_info["sended?"] = "n"
            pkt_info["crash"] = "y"
            pkt_info["DoS"] = "y"
            pkt_info["crash_info"] = "OSError - Host is down"
            print("[-] Crash packet causes HOST DOWN. Test finished.")
            is_crashed = True

    else: pass

    time.sleep(0.1)
    if(pkt_info == ""): pass
    else: logger.inputQueue(pkt_info)
    return is_crashed

def closed_state_fuzzing(target_addr, state_frame=NORMAL_STATE_FRAME):
    print("[-] current state: closed")
    for _ in range(MUTATION_CNT): 
        sock = closed(target_addr)
        is_crashed = fuz_send_pkt(target_addr, sock, bytes(random.choice(state_frame[RFCOMM_CLOSED_STATE]).gen()), RFCOMM_CLOSED_STATE)
        sock.close()
    time.sleep(0.1)
    return is_crashed

def term_wait_sec_check_state_fuzzing(target_addr, state_frame=NORMAL_STATE_FRAME):
    print("[-] current state: t_w_sec_check")
    for _ in range(MUTATION_CNT):
        sock = term_wait_sec(target_addr) 
        is_crashed = fuz_send_pkt(target_addr, sock, bytes(random.choice(state_frame[RFCOMM_TERM_WAIT_SEC_CHECK_STATE]).gen()), RFCOMM_TERM_WAIT_SEC_CHECK_STATE)
        sock.close()
    time.sleep(0.1)
    return is_crashed

def opened_state_fuzzing(target_addr, state_frame=NORMAL_STATE_FRAME):
    print("[-] current state: opened")
    for _ in range(MUTATION_CNT): 
        sock = opened_state(target_addr)
        is_crashed = fuz_send_pkt(target_addr, sock, bytes(random.choice(state_frame[RFCOMM_OPENED_STATE]).gen()), RFCOMM_OPENED_STATE,)
        sock.close()
    time.sleep(0.1)
    return is_crashed

def disc_wait_ua_state_fuzzing(target_addr, state_frame=NORMAL_STATE_FRAME):
    print("[-] current state: disc_w_ua")
    for _ in range(MUTATION_CNT): 
        sock = disc_wait_ua(target_addr)
        is_crashed = fuz_send_pkt(target_addr, sock, bytes(random.choice(state_frame[RFCOMM_DISC_WAIT_UA_STATE]).gen()), RFCOMM_DISC_WAIT_UA_STATE)
        sock.close()
    time.sleep(0.1)
    return is_crashed

def hidden_state_fuzzing(target_addr, state, state_frame=NORMAL_STATE_FRAME):
    print("[-] current state: "+state2str(state))
    for _ in range(MUTATION_CNT): 
        sock = hidden(target_addr, state)
        is_crashed = fuz_send_pkt(target_addr, sock, bytes(random.choice(state_frame[state]).gen()), state)
        sock.close()
    time.sleep(0.1)
    return is_crashed


def mutation_in_normal_state(target_addr):
    print("[-] normal mutation")
    is_crashed = closed_state_fuzzing(target_addr)
    if is_crashed: return True
    is_crashed = term_wait_sec_check_state_fuzzing(target_addr)
    if is_crashed: return True
    is_crashed = opened_state_fuzzing(target_addr)
    if is_crashed: return True
    is_crashed = disc_wait_ua_state_fuzzing(target_addr) 
    if is_crashed: return True

def mutation_in_adaptive_state(target_addr, adaptive_state_frame):
    print("[-] adaptive mutation")
    if len(adaptive_state_frame[RFCOMM_CLOSED_STATE]) != 0:
        is_crashed = closed_state_fuzzing(target_addr, state_frame=adaptive_state_frame)
        if is_crashed: return True
    if len(adaptive_state_frame[RFCOMM_TERM_WAIT_SEC_CHECK_STATE]) != 0:
        is_crashed = term_wait_sec_check_state_fuzzing(target_addr, state_frame=adaptive_state_frame)
        if is_crashed: return True
    if len(adaptive_state_frame[RFCOMM_OPENED_STATE]) != 0:
        is_crashed = opened_state_fuzzing(target_addr, state_frame=adaptive_state_frame)
        if is_crashed: return True
    if len(adaptive_state_frame[RFCOMM_DISC_WAIT_UA_STATE]) != 0:
        is_crashed = disc_wait_ua_state_fuzzing(target_addr, state_frame=adaptive_state_frame)
        if is_crashed: return True
    #print(adaptive_state_frame)
    # hidden state fuzzing
    for state in adaptive_state_frame:
        if state > 0x6:
            if len(adaptive_state_frame[state]) != 0:
                is_crashed = hidden_state_fuzzing(target_addr,state, state_frame=adaptive_state_frame)
                if is_crashed: return True

def logsave(loggerDict):
    loggerDict["end_time"] = str(datetime.now())
    loggerDict["count"] = {"all" : pkt_cnt, "crash" : crash_cnt, "passed" : pkt_cnt-crash_cnt}
    logger.inputQueue(loggerDict)
    logger.logUpdate()
    logger.init_info(loggerDict)

def fuzzing(target_addr, profile, port, adaptive_state_frame, test_info):
    global tmp
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
            is_crashed = mutation_in_normal_state(target_addr)
            if is_crashed:
                break
            is_crashed = mutation_in_adaptive_state(target_addr, adaptive_state_frame)
            if is_crashed:
                break
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