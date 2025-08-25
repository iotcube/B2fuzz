import argparse
import subprocess

def parse_option():
    parser = argparse.ArgumentParser(description='Bluetooth protocol fuzzer')
    parser.add_argument('--layer', choices=['L2CAP', 'RFCOMM'],
                        help='Protocol layer to test (L2CAP or RFCOMM)')

    # L2CAP options
    parser.add_argument('-p', '--pcap', dest='pcapng_file',
                        help='Path to pcapng file (for L2CAP)')
    parser.add_argument('-o', '--onetime', type=int, dest='onetime',
                        help='One-time mode (for L2CAP)')

    # RFCOMM options
    parser.add_argument('--ba', dest='target_addr',
                        help='Target Bluetooth address (for RFCOMM)')
    parser.add_argument('--visualize', '-v', dest='visualize', action='store_true',
                        help='Visualize state machine graph (for RFCOMM)')

    # NEW: pass-through fuzzing options for RFCOMM
    parser.add_argument('--fuzz', action='store_true',
                        help='Run adaptive fuzzing after building the RFCOMM state machine')
    parser.add_argument('--port', type=int, default=None,
                        help='RFCOMM channel/port override for fuzzing')
    parser.add_argument('--profile-name', type=str, default=None,
                        help='Override profile name passed to fuzzing()')
    # Time-based fuzzing passthrough (RFCOMM)
    parser.add_argument('--time', type=int, dest='time',
                        help='Total fuzzing time in seconds (split equally across CTRL+DLCIs)')
    parser.add_argument('--timeretry', action='store_true',
                        help='During each time slice, keep retrying session/DLCI until the slice ends')
    args = parser.parse_args()
    return args

def main():
    args = parse_option()
    if not args.layer:
        print('List of supported protocol:')
        print('1. L2CAP')
        print('2. RFCOMM')
        layer = input('Choose option > ')
        if layer == '1':
            args.layer = 'L2CAP'
        elif layer == '2':
            args.layer = 'RFCOMM'
        else:
            print('Invalid selection. Exiting.')
            return

    if args.layer == 'L2CAP':
        args_list = ['python3', 'l2cap/main.py']
        if args.pcapng_file is not None:
            args_list.extend(['-p', args.pcapng_file])
        if args.onetime is not None:
            args_list.extend(['-o', str(args.onetime)])
        subprocess.run(args_list)

    elif args.layer == 'RFCOMM':
        args_list = ['python3', 'rfcomm/main.py']

        if args.target_addr is not None:
            args_list.extend(['--ba', args.target_addr])

        # Prefer short flag -v so it works whether main.py supports --visualize or not
        if args.visualize:
            args_list.append('-v')

        # NEW: pass through fuzzing-related flags
        if args.fuzz:
            args_list.append('--fuzz')
        if args.port is not None:
            args_list.extend(['--port', str(args.port)])
        if args.profile_name is not None:
            args_list.extend(['--profile-name', args.profile_name])
        if args.time is not None:
            args_list.extend(['--time', str(args.time)])
        if args.timeretry:
            args_list.append('--timeretry')
        subprocess.run(args_list)
    else:
        print('Invalid protocol selection.')

if __name__ == '__main__':
    main()
