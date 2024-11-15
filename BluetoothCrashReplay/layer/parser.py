import pathlib

class Parser:
    def __init__(self):
        self.raw_text: str = ''
        self.filepath: pathlib.Path = pathlib.Path()
        self.info: dict = dict()
        self.raw_text_lines: list = []
        self.pkts: list = []

    def get_raw_text(self):
        with open(self.filepath, mode='r', encoding='utf-8') as f:
            self.raw_text = f.read()