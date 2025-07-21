import sys
import argparse
import json
from collections import OrderedDict
from termcolor import colored
from lib.scan import bluetooth_classic_scan
from lib.search import bluetooth_services_and_protocols_search
from modules.construct_sm import construct_sm, expand_sm, print_sm
from modules.mutation_new import fuzzing

test_info = OrderedDict()
test_info["tool_name"] = "b2fuzz"
test_info["interface"] = "Bluetooth"
test_info["toolVer"] = "1.0.0"
test_info["protocol"] = "RFCOMM"

def main():
    """
    Main logic for RFCOMM fuzzing. Handles --ba option if target address specified.
    """
    global test_info
    parser = argparse.ArgumentParser(description="RFUZZ RFCOMM main entry point")
    parser.add_argument('--ba', dest='target_addr', help='Target Bluetooth address')
    args = parser.parse_args()

    # [1] Use CLI addr or scan
    if args.target_addr:
        target_addr = args.target_addr
        test_info["bdaddr"] = target_addr
        print(colored(f"[1/5] Using CLI target address: {target_addr}", "red", "on_white"))
    else:
        print(colored("[1/5] SCANNING DEVICES", "red", "on_white"))
        test_info, target_addr = bluetooth_classic_scan(test_info)

    # [2] Search and select RFCOMM profile
    print(colored("[2/5] SEARCHING AVAILABLE PROFILES", "red", "on_white"))
    while True:
        test_info, target_service = bluetooth_services_and_protocols_search(target_addr, test_info)
        if target_service is False:
            print("Service not found on target device")
            sys.exit()
        target_protocol = target_service['protocol']
        target_profile = target_service['name']
        target_profile_port = target_service['port']
        if target_protocol == "RFCOMM":
            break
        else:
            print("[-] It is not RFCOMM Protocol.")
            continue
    print(colored("===================TARGET SUMMARY===================", "yellow"))
    print(colored(json.dumps(test_info, ensure_ascii=False, indent="\t"), "yellow"))
    print(colored("======================================================", "yellow"))

    # [3] Construct base state machine
    chan_list = []
    chan_list.append(target_profile_port)
    print(colored("[3/5] CONSTRUCTING BASE STATE MACHINE", "red", "on_white"))
    sm = construct_sm(target_addr, chan_list)


    # [4] Expand state machine
    # print(colored("[4/5] EXPANDING STATE MACHINE", "red", "on_white"))
    # sm, path = expand_sm(sm, target_profile_port, target_addr)
    test_info["state machine"] = print_sm(sm)
    sys.exit()

    # [5] Perform stateful fuzzing
    if sm:
        print(colored("[5/5] FUZZING", "red", "on_white"))
        fuzzing(target_addr, target_profile, target_profile_port, sm, test_info, path)

if __name__ == '__main__':
    main()