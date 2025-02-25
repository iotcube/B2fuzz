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

# Current time
now = datetime.now()
t = str(now)[11:19].replace(':',"",2)

# Day information for log file
today = date.today()
today = today.isoformat()
d = today[2:4] + today[5:7] + today[8:10]
def get_logtime():
    global d
    global t
    return d+t


logger = Logger(get_logtime())
"""
logger global variable for collecting sended frame
"""

tmp = 0

crash_cnt = 0
"""
Crash counter: Number of crash
"""
pkt_cnt = 0
"""
Packet counter: Number of sended frame
"""

MUTATION_CNT = 200
"""
Number of frame to send in one state
"""

def _pf(const):
    """
    NOT USED
    """
    return const | (1 << 4)

def state2str(state):
    """
        Translate state code to string

        Parameters
        ----------
         - state : [int] State code defined in `modules.pairing`

        Raises
        ----------
         - 

        Returns
        ----------
         - [string] Name of each state
    """
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
    """
    NOT USED\n
    RFUZZ collects original frame.
    """
    payload = {}
    payload['Address'] = hex(pkt[0])
    payload['Control'] = {
        'frame type': hex(_pf(pkt[1]))
    }
    payload['length'] = ((pkt[2] - 1) << 1)
    payload['data'] = pkt[3:-1].hex()
    payload['fcs'] = hex(pkt[-1])
    return payload

def fuz_send_pkt(bt_addr, sock, pkt, state,path=None, channel_to_ctrl=0):
    """
    Send mutated RFCOMM frame to target device.\n
    
    Parameters
    ----------
     - bt_addr: [string] MAC address of target devvice
     - sock: bluetooth socket
     - pkt: RFCOMM frame class defined `layer.rfcoomm.types`
     - state: current state
     - path: [list] list storing the path to new state
     - channel_to_ctrl: [int] profile channel to control with RFCOMM MX command

    Raises
    ----------
     - Connection error
     - bluetooth error

    Returns
    ----------
     - [bool] is_crashed: True if crash is detected else False

    Errno
    ------
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

    # [1] send RFCOMM frame
    try:
        if pkt not in RFCOMM_CMD:
            tmp_pkt = pkt.gen(channel=channel_to_ctrl, fuzz=True)
            sock.send(tmp_pkt)
        else:
            tmp_pkt = UIH.gen(channel=CTRL_CHANNEL, channel_to_ctrl=channel_to_ctrl, transition=False,fuzz=True, mx_type=pkt)
            sock.send(tmp_pkt)

    # [2] Make logger information
        pkt_info = {}
        pkt_info['no'] = pkt_cnt
        pkt_info['protocol'] = 'RFCOMM'
        pkt_info['sended_time'] = str(datetime.now())
        pkt_info['payload'] = tmp_pkt
        pkt_info['crash'] = 'n'
        pkt_info['state'] = {"name": state2str(state), "src": (str(path[state - 5][0]).split())[1], "tr": str(path[state - 5][1])} if path else state2str(state)

    # [3] If crash(connection error) is detected, write it to logger
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
            pkt_info["payload"] = tmp_pkt
            pkt_info["state"] = {"name": state2str(state), "src": (str(path[state - 5][0]).split())[1], "tr": str(path[state - 5][1])} if path else state2str(state)
            pkt_info["sended?"] = "n"			
            pkt_info["crash"] = "y"
            pkt_info["crash_info"] = "ConnectionResetError"
            is_crashed = True
    # [3] If crash(bluetooth error) is detected, write it to logger
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
        pkt_info["payload"] = tmp_pkt
        pkt_info["state"] = {"name": state2str(state), "src": (str(path[state - 5][0]).split())[1], "tr": str(path[state - 5][1])} if path else state2str(state)
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
    """
    Fuzzing in CLOSED state with anomaly detection.
    
    Parameters
    ----------
     - target_addr: [string] target devices MAC address
     - state_frame: adaptive state machine
     - ch: [int] target profile number

    Returns
    ----------
     - [bool] True if crash is found else False

    """
    print("[-] current state: closed")
    global tmp_pkt
    global crash_cnt
    #sock = closed(target_addr)

    # [1] Repeat fuzzing MUTATION_CNT times
    for _ in range(MUTATION_CNT): 

        # [2] Set socket state to CLOSED
        sock = closed(target_addr)

        # [3] Perform fuzzing with the frame in the adaptive state machine
        if sock:
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[CTRL_CHANNEL][CLOSED]), CLOSED)
            sock.close()

        # [4] After fuzzing, run anomaly detection logic
            
            # ANOMALY DETECTION
            sock = closed(target_addr)
            if sock:
                sock.close()
            else:
                print(f"[-] Crash Found - State violation detected at closed_state")
                print("Crash Packet :", tmp_pkt)
                crash_cnt += 1

                logger.Q_crash_cnt += 1
                print("Crash packet count : ", crash_cnt)
                pkt_info = {}
                pkt_info["no"] = pkt_cnt
                pkt_info["protocol"] = "RFCOMM"
                pkt_info["sended_time"] = str(datetime.now())
                pkt_info["payload"] = tmp_pkt
                pkt_info["state"] = "closed_state"
                pkt_info["sended?"] = "n"			
                pkt_info["crash"] = "y"
                pkt_info["crash_info"] = "State violation"
                is_crashed = True
                if(pkt_info == ""): pass
                else: logger.inputQueue(pkt_info)
                break

    #sock.close()
    return is_crashed

def open_ctrl_ch_state_fuzzing(target_addr, state_frame, ch=0):
    """
    Fuzzing in OPEN_CTRL_CH state with anomaly detection.
    
    Parameters
    ----------
     - target_addr: [string] target devices MAC address
     - state_frame: adaptive state machine
     - ch: [int] target profile number
  
    Returns
    ----------
    - [bool] True if crash is found else False

    """
    global tmp_pkt
    global crash_cnt
    print("[-] current state: open_ctrl_ch")
    #sock = opened_ctrl_ch(target_addr)

    # [1] Repeat fuzzing MUTATION_CNT times
    for _ in range(MUTATION_CNT): 

        # [2] Set socket state to OPEN_CTRL_CH
        sock = opened_ctrl_ch(target_addr)
        if sock:

            # [3] Perform fuzzing with the frame in the adaptive state machine
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[CTRL_CHANNEL][OPENED_CTRL_CH]), OPENED_CTRL_CH)
            sock.close()

            # [4] After fuzzing, run anomaly detection logic

            # ANOMALY DETECTION
            sock = opened_ctrl_ch(target_addr)
            if sock:
                sock.close()
            else:
                print(f"[-] Crash Found - State violation detected at opened_ctrl_chanel")
                print("Crash Packet :", tmp_pkt)
                crash_cnt += 1

                logger.Q_crash_cnt += 1
                print("Crash packet count : ", crash_cnt)
                pkt_info = {}
                pkt_info["no"] = pkt_cnt
                pkt_info["protocol"] = "RFCOMM"
                pkt_info["sended_time"] = str(datetime.now())
                pkt_info["payload"] = tmp_pkt
                pkt_info["state"] = "opened_ctrl_channel_state"
                pkt_info["sended?"] = "n"			
                pkt_info["crash"] = "y"
                pkt_info["crash_info"] = "State violation"
                is_crashed = True
                if(pkt_info == ""): pass
                else: logger.inputQueue(pkt_info)
                break

    #sock.close()
    return is_crashed

def closed_normal_ch_state_fuzzing(target_addr, state_frame, ch):
    """
    Fuzzing in CLOSED_NORMAL_CH state with anomaly detection.
    
    Parameters
    ----------
     - target_addr: [string] target devices MAC address
     - state_frame: adaptive state machine
     - ch: [int] target profile number


    Returns
    ----------
    - [bool] True if crash is found else False
    """


    print("[-] current state: closed_normal_ch")
    global tmp_pkt
    global crash_cnt
    #sock = closed_normal_ch(target_addr, ch)

    # [1] Repeat fuzzing MUTATION_CNT times
    for _ in range(MUTATION_CNT): 

        # [2] Set socket state to CLOSED_NORMAL_CH
        sock = closed_normal_ch(target_addr, ch)
        if sock:

            # [3] Perform fuzzing with the frame in the adaptive state machine
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[ch][CLOSED_NORMAL_CH]), CLOSED_NORMAL_CH, channel_to_ctrl=ch)
            sock.close()

            # [4] After fuzzing, run anomaly detection logic

            # ANOMALY DETECTION
            sock = closed_normal_ch(target_addr, ch)
            if sock:
                sock.close()
            else:
                print(f"[-] Crash Found - State violation detected at closed normal ch")
                print("Crash Packet :", tmp_pkt)
                crash_cnt += 1

                logger.Q_crash_cnt += 1
                print("Crash packet count : ", crash_cnt)
                pkt_info = {}
                pkt_info["no"] = pkt_cnt
                pkt_info["protocol"] = "RFCOMM"
                pkt_info["sended_time"] = str(datetime.now())
                pkt_info["payload"] = tmp_pkt
                pkt_info["state"] = "closed normal ch"
                pkt_info["sended?"] = "n"			
                pkt_info["crash"] = "y"
                pkt_info["crash_info"] = "State violation"
                is_crashed = True
                if(pkt_info == ""): pass
                else: logger.inputQueue(pkt_info)
                break

    #sock.close()
    return is_crashed

def opened_normal_ch_state_fuzzing(target_addr, state_frame, ch):
    """
    Fuzzing in OPENED_NORMAL_STATE state with anomaly detection.
    
    Parameters
    ----------
    - target_addr: [string] target devices MAC address
    - state_frame: adaptive state machine
    - ch: [int] target profile number


    Returns
    ----------
    - [bool] True if crash is found else False
    """
    print("[-] current state: opened_normal_ch")
    global tmp_pkt
    global crash_cnt
    #sock = open_normal_ch(target_addr, ch)

    # [1] Repeat fuzzing MUTATION_CNT times
    for _ in range(MUTATION_CNT): 

        # [2] Set socket state to OPEN_NORMAL_CH
        sock = open_normal_ch(target_addr, ch)
        if sock:

            # [3] Perform fuzzing with the frame in the adaptive state machine
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[ch][OPENED_NORMAL_CH]), OPENED_NORMAL_CH, channel_to_ctrl=ch)
            sock.close()
        

            # [4] After fuzzing, run anomaly detection logic

            # ANOMALY DETECTION
            sock = open_normal_ch(target_addr, ch)
            if sock:
                sock.close()
            else:
                print(f"[-] Crash Found - State violation detected at opened_normal_channel_state")
                print("Crash Packet :", tmp_pkt)
                crash_cnt += 1

                logger.Q_crash_cnt += 1
                print("Crash packet count : ", crash_cnt)
                pkt_info = {}
                pkt_info["no"] = pkt_cnt
                pkt_info["protocol"] = "RFCOMM"
                pkt_info["sended_time"] = str(datetime.now())
                pkt_info["payload"] = tmp_pkt
                pkt_info["state"] = "opened_normal_channel_state"
                pkt_info["sended?"] = "n"			
                pkt_info["crash"] = "y"
                pkt_info["crash_info"] = "State violation"
                is_crashed = True
                if(pkt_info == ""): pass
                else: logger.inputQueue(pkt_info)
                break

    #sock.close()
    return is_crashed


def opened_normal_ch_with_msc_state_fuzzing(target_addr, state_frame, ch):
    """
    Fuzzing in OPEN_NORMAL_CH_WITH_MSC state with anomaly detection.
    
    Parameters
    ----------
    - target_addr: [string] target devices MAC address
    - state_frame: adaptive state machine
    - ch: [int] target profile number


    Returns
    ----------
    - [bool] True if crash is found else False
    """
    print("[-] current state: opened_normal_ch_with_msc")
    global tmp_pkt
    global crash_cnt
    #sock, _ = open_normal_ch_with_msc(target_addr, ch)

    # [1] Repeat fuzzing MUTATION_CNT times
    for _ in range(MUTATION_CNT):

        # [2] Set socket state to OPEN_NORMAL_CH_WITH_MSC
        sock, _ = open_normal_ch_with_msc(target_addr, ch)
        if sock:

            # [3] Perform fuzzing with the frame in the adaptive state machine
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(state_frame[ch][OPENED_NORMAL_CH_WITH_MSC]), OPENED_NORMAL_CH_WITH_MSC, channel_to_ctrl=ch)
            sock.close()

            # [4] After fuzzing, run anomaly detection logic

            # ANOMALY DETECTION
            sock, _ = open_normal_ch_with_msc(target_addr, ch)
            if sock:
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
                pkt_info["payload"] =tmp_pkt
                pkt_info["state"] = "opened normal channel(after msc)"
                pkt_info["sended?"] = "n"			
                pkt_info["crash"] = "y"
                pkt_info["crash_info"] = "State violation"
                is_crashed = True
                if(pkt_info == ""): pass
                else: logger.inputQueue(pkt_info)
                break

    #sock.close()
    return is_crashed

def new_state_fuzzing(target_addr, state_frame, ch, state, path):
    """
    Fuzzing in new state with anomaly detection.
    
    Parameters
    ----------
    - target_addr: [string] target devices MAC address
    - state_frame: adaptive state machine
    - ch: [int] target profile number


    Returns
    ----------
    - [bool] True if crash is found else False
    """
    print(f"[-] current state: new_state{state - 4}")
    global tmp_pkt
    global crash_cnt
    #if path[state - 5][0] == open_normal_ch_with_msc:
    #    sock, _ = open_normal_ch_with_msc(target_addr, ch)
    #else:
    #    sock = path[state - 5][0](target_addr, ch)
    #if sock:
    #    sock.send(path[state - 5][1])
    #else:
    #    sock = False


    # [1] Repeat fuzzing MUTATION_CNT times
    for _ in range(MUTATION_CNT):

        # [2] Set socket state to new state
        if path[state - 5][0] == open_normal_ch_with_msc:
            sock, _ = open_normal_ch_with_msc(target_addr, ch)
        else:
            sock = path[state - 5][0](target_addr, ch)
        if sock:
            sock.send(path[state - 5][1])
        else:
            sock = False
        if sock:

            # [3] Perform fuzzing with the frame in the adaptive state machine
            is_crashed = fuz_send_pkt(target_addr, sock, random.choice(RFCOMM_CMD + RFCOMM_FRAME), state, path, channel_to_ctrl=ch)
            sock.close()

            # [4] After fuzzing, run anomaly detection logic

            # ANOMALY DETECTION
            if path[state - 5][0] == open_normal_ch_with_msc:
                sock, _ = open_normal_ch_with_msc(target_addr, ch)
            else:
                sock = path[state - 5][0](target_addr, ch)
            if sock:
                sock.send(path[state - 5][1])
            else:
                sock = False
            if sock:
                sock.close()
            else:
        
                print(f"[-] Crash Found - State violation detected at {state2str(state)}")
                print("Crash Packet :", tmp_pkt)
                crash_cnt += 1

                logger.Q_crash_cnt += 1
                print("Crash packet count : ", crash_cnt)
                pkt_info = {}
                pkt_info["no"] = pkt_cnt
                pkt_info["protocol"] = "RFCOMM"
                pkt_info["sended_time"] = str(datetime.now())
                pkt_info["payload"] = tmp_pkt
                pkt_info["state"] = {"name": state2str(state), "src": (str(path[state - 5][0]).split())[1], "tr": str(path[state - 5][1])}
                pkt_info["sended?"] = "n"			
                pkt_info["crash"] = "y"
                pkt_info["crash_info"] = "State violation"
                is_crashed = True
                if(pkt_info == ""): pass
                else: logger.inputQueue(pkt_info)
                break

    #sock.close()
    return is_crashed

def traverse_adaptive_sm(target_addr, sm, path):
    """
    Traverse adaptive state machine\n

    Parameters
    ----------
    - target_addr: [string] target devices MAC address
    - sm: adaptive state machine
    - path: [list] list storing path to new state


    Returns
    ----------
    - [bool] True if crash is found else False
    """

    # [1] For each channel in adaptive state machine
    for channel in sm:

    # [2] For each state in per-channel state machine
        for state in sm[channel]:

            # [3] Fuzzing each state
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
    """
    Save loggerdict to log file

    Parameters
    ----------
    - loggerDict: [dictionary] Information to save


    Returns
    ----------
    - None
    """

    # [1] Add end_time, count information to loggerDict
    loggerDict["end_time"] = str(datetime.now())
    loggerDict["count"] = {"all" : pkt_cnt, "crash" : crash_cnt, "passed" : pkt_cnt-crash_cnt}
    
    # [2] save loggerDict to log file
    logger.inputQueue(loggerDict)
    logger.logUpdate()
    logger.init_info(loggerDict)



def fuzzing(target_addr, profile, port, adaptive_state_frame, test_info, path):
    """
    Perform stateful fuzzing

    Parameters
    ----------
    - target_addr: [string] MAC address of target 
    - profile: [int] target profile number
    - port: [int] target profile number
    - adaptive_state_frame: adaptive state machine for fuzzing
    - test_info: test information for logging
    - path: [list] list storing path to new state


    Returns
    ----------
    - None
    """
    global tmp
    global crash_cnt
    global logger
    now = datetime.now()
    tmp = 0
    i=0
    crash2 = False
    test_info["starting_time"] = str(now)
    logger.init_info(test_info)
    if(profile == "None" or port == "None"):
        print('Cannot Fuzzing')
        return
    print("Start Fuzzing... Please hit Ctrl + C to finish...")
    logger.start = time.time()
    try:

    # [1] Fuzzing loop

        while True:

    # [2] save fuzzing start indicator to log
            logger.inputQueue("***********************Fuzz_start********************")
            print("[+] Tested %d packets" % (pkt_cnt))
            loggerDict = {}
            #is_crashed = False
    
    # [3] traverse adaptive state machine and fuzz
            is_crashed = traverse_adaptive_sm(target_addr, adaptive_state_frame, path)
            if is_crashed:
                logger.inputQueue("**ITEREND**")
                logsave(loggerDict)
    
    # [4] After fuzzing test connection with l2ping command.
    # if there is connection fail in l2ping, stop loop
                
                if l2ping(target_addr) == False:
                    break
                else:
                    time.sleep(1)
                    continue
            #is_crashed = mutation_in_adaptive_state(target_addr, adaptive_state_frame)
            #if is_crashed:
            #    break
    # [5] Save collected log information
            logger.inputQueue("**ITEREND**")
            i += 1
            logsave(loggerDict)
            print("********************************************************************")
           
            #if pkt_cnt > 2000000:
            #    print('[*] Save logfile')
            #    print('iteration END@@@@@@@@@@')
            #    logsave(loggerDict)
            #    break

    # [6] if there is crash, save log to file
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