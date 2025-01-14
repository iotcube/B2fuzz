from datetime import datetime
from pprint import pprint
from modules import *
from lib import *
from time import sleep
test_info = OrderedDict()
test_info["tool_name"] = "b2fuzz"
test_info["interface"] = "Bluetooth"
test_info["toolVer"] = "1.0.0"
test_info["protocol"] = "RFCOMM"

def main():
    global test_info
    test_info, target_addr = bluetooth_classic_scan(test_info)

    while(1):
        test_info, target_service = bluetooth_services_and_protocols_search(target_addr, test_info)
        if target_service is False:
            print("Service not found on target device")
            sys.exit()
        target_protocol = target_service['protocol']
        target_profile = target_service['name']
        target_profile_port = target_service['port']
        if(target_protocol == "RFCOMM"):
            break
        else:
            continue
    print("\n===================Test Informatoin===================")
    print(json.dumps(test_info, ensure_ascii=False, indent="\t"))
    print("======================================================\n")
    #adaptive_state_frame = construct_android_adaptive_sm(target_addr)
    ##input()
    #pprint(parse_adaptive_state(adaptive_state_frame))
    #test_info["state machine"] = parse_adaptive_state(adaptive_state_frame)
    #start_time = str(datetime.now())
    #print('[*] Fuzzing Start...')
    #print(f'[*] Fuzzing Start Time : {start_time}')
    #test_info["starting_time"] = start_time
    #
    #fuzzing(target_addr, target_profile, target_profile_port, adaptive_state_frame, test_info)
    c = 0
    
    #for _ in range(10):
    #    if open_channel(target_profile_port, target_addr):
    #        c += 1
    #print(f"crash: {c} / attempt: 10")
    #open_channel(target_profile_port, target_addr)
    
    #open_rfcomm_channel(target_profile_port, target_addr)
    #sock= open_ch_n(target_addr, target_profile_port)
    #sock, new_dlci = open_new_chan(target_addr, target_profile_port)
    #if sock:
    #    sock = new_chan_msc(sock, new_dlci>>1, new_dlci&0b1)
    #if sock:
    #    if not new_chan:
    #        print("[-] send pkt")
    #        sock.send(bytes(DATA.gen(channel=target_profile_port, length=120)))
    #        try:
    #            res = sock.recv(MTU)
    #        except:
    #            print("[-] no res")
    #            return False
    #        print(f"[-] response: {res}")
    #    else:
    #        print("[-] send pkt")
    #        sock.send(bytes(DATA.gen(channel=new_chan, length=120, dir=dir)))
    #        try:
    #            res = sock.recv(MTU)
    #        except:
    #            print("[-] no res")
    #            return False
    #        print(f"[-] response: {res}")
    construct_sm(target_addr, target_profile_port)
    
if __name__ == '__main__':
    main()
