import bluetooth
from termcolor import colored
from pprint import pprint

def bluetooth_services_and_protocols_search(bt_addr, test_info):
    """
    Search services and protocols. Prompts the user to select one service,
    or type 'all' to select all available services.
    """
    try:
        services = bluetooth.find_service(address=bt_addr)
    except bluetooth.btcommon.BluetoothError as e:
        print(colored(f"[-] Service discovery failed: {e}", "red"))
        return test_info, False

    if not services:
        print("[-] No services found!")
        return test_info, False
    
    # Print the list of found services (this part is unchanged)
    print(colored(f"[+] Found {len(services)} profile(s) in the device", "yellow"))
    print("  {:<4} {:<30} {:<15} {:<15} {:<15}".format("[#]", "[Service Name]", "[Protocol]", "[Port (Ch.)]", "[ID]"))
    for i, serv in enumerate(services):
        protocol = serv.get("protocol") or "Unknown"
        port = str(serv.get("port")) if serv.get("port") is not None else "N/A"
        profile_id = f"0x{serv['profiles'][0][0]}" if serv.get("profiles") and serv["profiles"][0][0] else "Unknown"
        name = serv.get("name")
        if isinstance(name, bytes):
            name = name.decode('utf-8', 'ignore')
        name = name or "Unknown"
        print("  {:<4} {:<30} {:<15} {:<15} {:<15}".format(
            f"{i:02d}.", name[:30], protocol, port, profile_id
        ))

    print("-----------------------------------------------------------------------------------")
    
    # --- MODIFIED INPUT LOOP ---
    while(True):
        # Update the prompt to include the 'all' option
        user_input_str = input("[Q] Select a profile to fuzz (e.g., 0) or type 'all': ")
        
        # Check for the 'all' command
        if user_input_str.strip().lower() == 'all':
            serv_chosen = services # Select all services
            break
        
        # If not 'all', try to process it as a number
        try:
            user_input_num = int(user_input_str)
            if 0 <= user_input_num < len(services):
                # To keep the return type consistent, we return a list containing the single choice
                serv_chosen = [services[user_input_num]]
                break
            else:
                print("[-] Out of range.")
        except ValueError:
            print("[-] Invalid input. Please enter a number or 'all'.")

    # The rest of the function now works with a list of chosen services.
    # We'll populate test_info based on the first service in the list for summary purposes.
    first_service = serv_chosen[0]
    test_info["service"] = first_service.get("name")
    test_info["protocol"] = first_service.get("protocol")
    test_info["port"] = first_service.get("port")

    return test_info, serv_chosen