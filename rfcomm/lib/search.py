import bluetooth
from termcolor import colored
from pprint import pprint

def bluetooth_services_and_protocols_search(bt_addr, test_info):
    """
    Search the services and protocols of device
    """
    services = bluetooth.find_service(address=bt_addr)

    if len(services) <= 0:
        print("[-] No services found!")
        return { "protocol": "None", "name": "None", "port": "None"}, False
    else:
        print(colored(f"[+] Found {len(services)} profile(s) in the device", "yellow"))
        print("  {:<4} {:<30} {:<15} {:<15} {:<15}".format("[#]", "[Service Name]", "[Protocol]", "[Port (Ch.)]", "[ID]"))
        for i, serv in enumerate(services):
            profile_id = "Unknown"
            # pprint(serv)
            if len(serv["profiles"]) > 0:
                profile_id = f"0x{serv['profiles'][0][0]}"
            
            name = serv.get("name", "Unknown")
            if name is None:
                name = "Unknown"
            else:
                name = name[:30]
            protocol = serv.get("protocol", "Unknown")
            port = str(serv.get("port", "N/A"))

            print("  {:<4} {:<30} {:<15} {:<15} {:<15}".format(
                f"{i:02d}.", name, protocol, port, profile_id
            ))

    print("-----------------------------------------------------------------------------------")
    while(True):
        user_input = int(input("[Q] Select a profile to fuzz : "))
        if user_input < len(services) and user_input > -1:
            idx = user_input
            serv_chosen = services[idx]
            break
        else:
            print("[-] Out of range.")        
  
    # print("Protocol for the profile [%s] : %s\n" % (serv_chosen["name"], serv_chosen["protocol"]))

    test_info["service"] = serv_chosen["name"]
    test_info["protocol"] = serv_chosen["protocol"]
    test_info["port"] = serv_chosen["port"]

    return test_info, serv_chosen