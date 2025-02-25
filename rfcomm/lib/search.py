import bluetooth


def bluetooth_services_and_protocols_search(bt_addr, test_info):
    """
    Search the services and protocols of device
    """
    print("\nStart scanning services...")
    print("\n\tList of profiles for the device")
    
    print("\n\tNo.\tprofile\tname\tprotocol\tport(Channel)")
    services = bluetooth.find_service(address=bt_addr)
    if len(services) <= 0:
        print("No services found")
        return { "protocol": "None", "name": "None", "port": "None"}, False
    else:
        i = 0
        for serv in services:
            if len(serv["profiles"]) == 0:
                print("\t%02d.\t[None]:\t%s\t%s\t%s" % (i, serv["name"], serv["protocol"], serv["port"]))
            else:
                print("\t%02d.\t[0x%s]:\t%s\t%s\t%s" % (i, serv["profiles"][0][0], serv["name"], serv["protocol"], serv["port"]))
            i += 1

    while(True):
        user_input = int(input("\nSelect a profile to fuzz : "))
        if user_input < len(services) and user_input > -1:
            idx = user_input
            serv_chosen = services[idx]
            break
        else:
            print("[-] Out of range.")        
  
    print("\n\tProtocol for the profile [%s] : %s\n" % (serv_chosen["name"], serv_chosen["protocol"]))

    test_info["service"] = serv_chosen["name"]
    test_info["protocol"] = serv_chosen["protocol"]
    test_info["port"] = serv_chosen["port"]

    return test_info, serv_chosen