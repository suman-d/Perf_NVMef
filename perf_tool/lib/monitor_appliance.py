#!/usr/bin/env python3


import os
import yaml
import time
import json
import datetime
import sys
from collections import OrderedDict
from pprint import pprint as pp
import toshibaeraptor


def cpu_mem_stat(eraptor, interval, duration):

    appliance_stat = OrderedDict()
    while duration > 0:
        data = eraptor.get_host_utilization()
        appliance_stat[datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")] = [data["hostUtilizations"][0]["cpuUsage"], data["hostUtilizations"][0]["memoryUsage"]]
        time.sleep(interval)
        duration -= 1

    return appliance_stat

def main(eraptor, test_type, dir, interval, duration):

    data = cpu_mem_stat(eraptor, interval, duration=duration)
    #filename = os.getcwd() + "/" + "appliance" + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + "cpu_mem_stat.json"
    filename = dir + "/" + test_type + "_" + "appliance" + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + "cpu_mem_stat.json"
    print(filename)
    with open(filename, 'w') as fp:
        json.dump(data, fp)


if __name__ == "__main__":

    # Loading the appliance IP and .pem file

    init_mgmt_ips = [sys.argv[3]]
    cert = os.path.abspath('ssdtoolbox.pem')
    duration = int(sys.argv[4])
    dir = sys.argv[2]
    test_type = sys.argv[1]
    # Connecting to the Appliance
    eraptor = toshibaeraptor.ToshibaERaptor(init_mgmt_ips, cert)

    main(eraptor, test_type, dir, interval=1, duration=duration)
