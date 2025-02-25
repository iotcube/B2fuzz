from datetime import datetime, date
from pprint import pprint
from modules.logger import *
from lib import *
from time import sleep

now = datetime.now()
t = str(now)[11:19].replace(':',"",2)
today = date.today()
today = today.isoformat()
d = today[2:4] + today[5:7] + today[8:10]

def get_logtime():
    global d
    global t
    return d+t


def logsave(logger):
    loggerDict = {}
    loggerDict["end_time"] = str(datetime.now())
    logger.inputQueue(loggerDict)
    logger.logUpdate()
    logger.init_info(loggerDict)


l = Logger("test_log")
l.inputQueue({"test": 1234})

logsave(logger=l)

