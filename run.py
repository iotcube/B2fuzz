from optparse import OptionParser
import subprocess

def parse_option():
    parse = OptionParser('usage sudo python3 main.py -p <[pcapngfile]>')
    parse.add_option('-p', '--pcap', dest = 'pcapng_file', help='./CommCapture/Airpod.pcapng')
    parse.add_option('-o', '--onetime', type=int, dest='onetime')
    (option, args) = parse.parse_args()
    return option.pcapng_file, option.onetime

def main():
    while True:
        print('1. l2cap')
        print('2. rfcomm')
        CommCapture_Path, is_onetime = parse_option()
        layer = int(input('> '))
        if layer == 1:
            args_list = ['python3.8', 'l2cap/main.py']
            if CommCapture_Path is not None:
                args_list.append('-p')
                args_list.append(CommCapture_Path)
            if is_onetime is not None:
                args_list.append('-o')
                args_list.append(str(is_onetime))
            subprocess.run(args_list)
            break
        elif layer == 2:
            subprocess.run(['python3.8', 'rfcomm/main.py'])
            break
        else: 
            continue

if __name__ == '__main__':
    main()
