from abc import ABC


class Sender(ABC):
    def __init__(self):
        self.bt_addr: str = ''
        self.total_crashcnt: int = 0
        self.total_sended_pktcnt: int = 0

    def connect(self):
        pass

    def run(self, mini_range_json):
        pass