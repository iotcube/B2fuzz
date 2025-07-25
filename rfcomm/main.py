import sys
import argparse
import json
from collections import OrderedDict
from termcolor import colored

# Your existing imports are correct
from lib.scan import bluetooth_classic_scan
from lib.search import bluetooth_services_and_protocols_search
from modules.construct_sm import construct_sm
from modules.mutation_new import fuzzing

test_info = OrderedDict()
test_info["tool_name"] = "b2fuzz"
test_info["interface"] = "Bluetooth"
test_info["toolVer"] = "1.0.0"
test_info["protocol"] = "RFCOMM"

def main():
    """
    Main logic for RFCOMM fuzzing. Handles --ba and --visualize option
    """
    global test_info
    parser = argparse.ArgumentParser(description="RFUZZ RFCOMM main entry point")
    parser.add_argument('--ba', dest='target_addr', help='Target Bluetooth address')
    parser.add_argument('--visualize', '-v', dest='visualize', action='store_true', help='Visualize state machine graph')
    args = parser.parse_args()

    # [1] Use CLI addr or scan (Your original logic is perfect)
    if args.target_addr:
        target_addr = args.target_addr
        test_info["bdaddr"] = target_addr
        print(colored(f"[1/5] Using CLI target address: {target_addr}", "red", "on_white"))
    else:
        print(colored("[1/5] SCANNING DEVICES", "red", "on_white"))
        target_addr = bluetooth_classic_scan(test_info)
        if not target_addr:
            print(colored("[-] No device selected or found. Exiting.", "red"))
            sys.exit()

    # [2] Search and select RFCOMM profile(s)
    print(colored("[2/5] SEARCHING AVAILABLE PROFILES", "red", "on_white"))
    
    # The search function now returns a LIST of chosen services
    test_info, services_to_test = bluetooth_services_and_protocols_search(target_addr, test_info)
    
    if not services_to_test:
        print("[-] No valid service selection. Exiting.")
        sys.exit()

    # Filter the selection to only include RFCOMM profiles with a valid port
    rfcomm_services = [
        s for s in services_to_test 
        if s.get('protocol') == 'RFCOMM' and s.get('port') is not None
    ]

    if not rfcomm_services:
        print(colored("[-] The selection did not contain any valid RFCOMM profiles to test.", "red"))
        sys.exit()

    # Create the chan_list from the final, filtered list of services.
    chan_list = [service['port'] for service in rfcomm_services]

    print(colored("===================TEST PLAN SUMMARY===================", "yellow"))
    print(colored(json.dumps(test_info, ensure_ascii=False, indent="\t"), "yellow"))
    print(colored(f"Will test the following RFCOMM channels: {chan_list}", "yellow"))
    print(colored("======================================================", "yellow"))

    # [3] Construct base state machine using the full channel list
    print(colored("[3/5] CONSTRUCTING BASE STATE MACHINE", "red", "on_white"))
    
    sm = construct_sm(target_addr, chan_list, VISUALIZE=args.visualize)

    # [4] Expand state machine (Your existing logic is fine)
    # print(colored("[4/5] EXPANDING STATE MACHINE", "red", "on_white"))
    # ...
    #test_info["state machine"] = print_sm(sm)
    sys.exit()

    # [5] Perform stateful fuzzing (Your existing logic is fine)
    if sm:
        print(colored("[5/5] FUZZING", "red", "on_white"))
        # Fuzzing typically targets one primary profile. We'll use the first one from the list.
        primary_service = rfcomm_services[0]
        fuzzing(target_addr, primary_service['name'], primary_service['port'], sm, test_info, path)

if __name__ == '__main__':
    main()