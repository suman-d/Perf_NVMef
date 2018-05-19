#!/usr/bin/env python3


import os
import yaml
import time
import numpy as np
import paramiko
import json
from pprint import pprint as pp
from lib import toshibaeraptor


def cpu_mem_stat(eraptor, interval, duration):
    cpu_stat = {"mean_stat": [], "raw_stat": []}
    memory_stat = {"mean_stat": [], "raw_stat": []}

    for i in range(0, duration, interval):
        data = eraptor.get_host_utilization()
        cpu_stat["raw_stat"].append(data["hostUtilizations"][0]["cpuUsage"])
        memory_stat["raw_stat"].append(data["hostUtilizations"][0]["memoryUsage"])

        time.sleep(interval)

    cpu_stat["mean_stat"] = round(float(np.mean(cpu_stat["raw_stat"])), 2)
    memory_stat["mean_stat"] = round(float(np.mean(memory_stat["raw_stat"])), 2)

    return cpu_stat, memory_stat

def ssd_smart_log(device):

    cmd_templete = "nvme smart-log {} -o json"
    cmd = cmd_templete.format(device)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    smart_info = ssh_stdout.read().decode("utf-8")

    return smart_info

def rnic_stat(interface):
    cmd_templete = "ethtool -S {}"
    cmd = cmd_templete.format(interface)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    rnic_info = ssh_stdout.read().decode("utf-8")

    rnic_info_list = [d.strip() for d in rnic_info.split("\n")]
    rnic_info_list.pop(0)
    rnic_info_list.pop()
    rnic_info_list = [d.split(":") for d in rnic_info_list]
    rnic_info_dict = { d[0].strip() : int(d[1].strip()) for d in rnic_info_list }

    rnic_info_dict_filer = { d: rnic_info_dict[d] for d in rnic_info_dict if d.startswith("rx_") or d.startswith("tx_")}

    return rnic_info_dict_filer

# Reading the config file
pwd = os.getcwd()
config = pwd + "/config/config1.yml"

with open(config, 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

# Appliance details
server = cfg['appliance']['ip']
username = cfg['appliance']['user']
password = cfg['appliance']['passwd']

# Creating a SSH object
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
ssh.connect(server, username=username, password=password)

# Loading the appliance IP and .pem file
cert = os.path.abspath('ssdtoolbox.pem')
init_mgmt_ips = [cfg['appliance']['ip']]

# Connecting to the Appliance
eraptor = toshibaeraptor.ToshibaERaptor(init_mgmt_ips, cert)

# Collecting the CPU and Memory Info
cpu_stat, mem_stat = cpu_mem_stat(eraptor, interval=2, duration=10)

pp(cpu_stat)
pp(mem_stat)

# Collecting the SMART info of all the backend SSD
ssds_list = eraptor.get_ssds_names()
smart_info_all_ssd = []
for ssd in ssds_list:
    smart_stat = {}
    smart_stat["ssd_name"] = ssd
    smart_stat["device"] = ssds_list[ssd]
    _smart_info = json.loads(ssd_smart_log(smart_stat["device"]))
    smart_stat["smart_data"] = _smart_info

    smart_info_all_ssd.append(smart_stat)

pp(smart_info_all_ssd)

# Collecting the NIC Stats (Only for the RNIC on which Portals are created)
portals = eraptor.get_portals_all()
rnic_names = [ p["netinterface"] for p in portals]
netstat_all_rnics = []
for rnic in rnic_names:
    r_stat = {}
    r_stat["name"] = rnic
    r_stat["stats"] = rnic_stat(rnic)

    netstat_all_rnics.append(r_stat)

pp(netstat_all_rnics)
