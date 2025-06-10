from datetime import datetime
from pprint import pprint
from termcolor import colored
from modules import *
from lib import *
from time import sleep
test_info = OrderedDict()
test_info["tool_name"] = "b2fuzz"
test_info["interface"] = "Bluetooth"
test_info["toolVer"] = "1.0.0"
test_info["protocol"] = "RFCOMM"

def main():
    """
    RFUZZ's main logic.
    1. Scan nearby bt device and select target profile.
    2. Perform fuzzing with RFCOMM state machine.

    Parameters
    ----------
     -
    
    Raises
    ----------
     -

    Returns
    ----------
     -
    """

    # [1] scan nearby bluetooth device
    global test_info
    print(colored("[1/5] SCANNING DEVICES", "red", "on_white"))
    test_info, target_addr = bluetooth_classic_scan(test_info)


    # [2] search target device's available profile and select target profile
    print(colored("[2/5] SEARCHING AVAILABLE PROFILES", "red", "on_white"))
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
    print(colored("===================TARGET SUMMARY===================", "yellow"))
    print(colored(json.dumps(test_info, ensure_ascii=False, indent="\t"), "yellow"))
    print(colored("======================================================", "yellow"))

    # [3] construct base state machine
    print(colored("[3/5] CONSTRUCTING BASE STATE MACHINE", "red", "on_white"))
    sm = construct_sm(target_addr, target_profile_port)

    # [4] expand base state machine to adaptive state machine
    print(colored("[4/5] EXPANDING STATE MACHINE", "red", "on_white"))
    exp_sm , path = expand_sm(sm, target_profile_port, target_addr)
    test_info["state machine"] = print_sm(exp_sm)
    
    # [5] Perform stateful fuzzing
    if exp_sm:
        print(colored("[5/5] FUZZING", "red", "on_white"))
        fuzzing(target_addr, target_profile, target_profile_port, exp_sm, test_info, path)
if __name__ == '__main__':
    main()
