import pathlib
import argparse
import config
import json
from typing import Union

from layer.l2cap.sender import L2CAPSender, L2CAPParser
from layer.rfcomm.sender import RFCOMMSender, RFCOMMParser

logger = config.logger
DEBUG_STR = '[   DEBUG] '

class PKTSender:
    def __init__(self):
        self.bt_addr: str = '' 
        self.filepath: pathlib.Path = pathlib.Path()
        self.parser: Union[RFCOMMParser, L2CAPParser] = None
        self.sender = None

    def get_logfile_path(self):
        arg_parser = argparse.ArgumentParser(description="Bluetooth replay module logfile path parser.")
        arg_parser.add_argument("--path", help="Path to the logfile for replaying.")
        args = arg_parser.parse_args()
        self.filepath = pathlib.Path.cwd() / args.path

    def set_parser(self):
        try:
            with open(self.filepath, mode='r', encoding='utf-8') as f:
                raw = f.read()
                if 'L2CAP' in raw:
                    self.parser = L2CAPParser(self.filepath)
                elif 'RFCOMM' in raw:
                    self.parser = RFCOMMParser(self.filepath)
                else:
                    pass

        except FileNotFoundError:
            logger.error('logfile not found.')
            exit(1)

    def get_bd_addr(self):
        try:
            with open(self.filepath.parent / 'info.wfl', mode='r', encoding='utf-8') as f:
                data = json.load(f)
                bd_addr = str(data['bdaddr'])
                return bd_addr
        except FileNotFoundError:
            logger.error('logfile not found.')
            exit(1)

    def set_sender(self):
        print(self.parser)
        if isinstance(self.parser,RFCOMMParser):
            self.sender = RFCOMMSender(self.get_bd_addr())
            logger.info('RFCOMM Send')
        if isinstance(self.parser,L2CAPParser):
            self.sender = L2CAPSender(self.get_bd_addr())
            logger.info('L2CAP Send')

    def run(self):
        self.get_logfile_path()
        self.set_parser()
        if self.parser is None:
            logger.error('Not valid logfile format')
            exit(1)
        else:
            self.parser.get_info()
            self.parser.get_pkts()
        self.set_sender()
        self.sender.run(self.filepath.parent / 'packets.wfl')

if __name__ == '__main__':
    sender = PKTSender()
    sender.run()
