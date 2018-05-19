import psutil
import datetime
import time
import json
import socket
import os
import sys
from collections import OrderedDict
from pprint import pprint as pp


def monitor_cpu_mem_util(duration):

    system_stat = OrderedDict()
    while duration > 0:
        system_stat[datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")] = [psutil.cpu_percent(), psutil.virtual_memory()[2]]
        time.sleep(1)
        duration -= 1

    return system_stat

def main(duration, test_type):

    data = monitor_cpu_mem_util(duration)
    filename = os.getcwd() + "/" + test_type + "_"+ socket.gethostname() + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + "cpu_mem_stat.json"

    with open(filename, 'w') as fp:
        json.dump(data, fp)

if __name__ == "__main__":

    duration = int(sys.argv[1])
    test_type = sys.argv[2]
    main(duration, test_type)
