import abc

class RFCOMM(abc.ABC):
    def __init__(self):
        self.addr = 0
        self.control = None 
        self.length = 0
        self.data = None
        self.fcs = 0