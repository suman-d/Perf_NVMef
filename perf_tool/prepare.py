#!/usr/bin/env python3

'''This is part of Perf_NVMef Tool Kit
   Internally used by nvmef_perf.py to prepare the appliance and hosts'''

# Author : Suman Debnath
# E-Mail : suman.debnath@toshiba-tsip.com
# Last Update: 13-March-2018
# Version: 1.1


import yaml
import os
import sys
import random
import socket
import time
import paramiko
import json
from lib import toshibaeraptor
from lib import nvmecli_cmds
from pprint import pprint as pp


def setup(cfg, ssh):

    cert = os.path.abspath('ssdtoolbox.pem')

    # Reading the Appliance related info(IP, Storage Configuration, etc.)
    init_mgmt_ips = [cfg['appliance']['ip']]
    no_ssds = cfg['storage_config']['no_ssds_per_group']
    no_ssd_groups = cfg['storage_config']['no_ssd_group']
    no_targets = cfg['storage_config']['no_targets']
    ns_block_size = cfg['storage_config']['namespace_blocksize']
    chunk_size = cfg['storage_config']['ssd_group_chunk_size']
    init1_portals = cfg['initiator1']['portals']
    init2_portals = cfg['initiator2']['portals']

    localhost_hostname = cfg['initiator1']['name']
    remote_host = cfg['initiator2']['ip']
    remote_passwd = cfg['initiator2']['passwd']
    remote_user = cfg['initiator2']['user']
    remote_hostname = cfg['initiator2']['name']


    # Disconnecting targets from the initiators(if any)
    print("*************************************************************************************************")
    print("Disconnecting any exisiting targets from Host1 (if any)")
    nvmecli_cmds.disconnect_targets()

    print("Disconnecting any exisiting targets from Host2 (if any)")

    cmd = "nvme list -o json"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    devices = ssh_stdout.read().decode("utf-8").strip()
    devices = json.loads(devices)
    d_list = []
    if devices:
        for d in devices["Devices"]:
            d_list.append(d["DevicePath"])

    d_list = [ d.rsplit("n", 1)[0] for d in d_list]
    cmd_template = "nvme disconnect -d {}"

    for device in d_list:
        cmd = cmd_template.format(device)
        print("Running this in the remote host : {}".format(cmd))
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)

    # Connecting to the Appliance
    eraptor = toshibaeraptor.ToshibaERaptor(init_mgmt_ips, cert)

    # Clean the setup, remove any targets and ssd_groups
    print("*************************************************************************************************")
    print("Clearning the exisiting configuration in the Appliance")
    eraptor.cleanup()
    print("Cleanup is done")

    # Check if enough SSDs are present in the appliance or not
    ssds_list = eraptor.get_ssds_names()
    total_ssds = len(ssds_list.keys())

    if no_ssds*no_ssd_groups > total_ssds:
        print("The Appliance doesnt have enough no. of SSDs.")
        print("You asked for {} and available is {}".format(no_ssds, total_ssds))
        sys.exit(0)
    elif no_ssds == 0:
        print("Can not create a SSD Group with 0 SSD :)")
        sys.exit(0)

    print("*************************************************************************************************")

    # Create SSD Group with the no. of SSDs
    print("Creating {} no. of SSD Groups each with {} SSDs".format(no_ssd_groups, no_ssds))
    selected_ssds = list(ssds_list.keys())[:no_ssd_groups:]

    for ssd in selected_ssds:
        group_name = "group-{}".format(ssd.split("SSD")[1])
        print("Creating the SSD Group with name {} using SSD {}".format(group_name, ssd))
        eraptor.create_ssd_group(group_name, [ssd])
        print(ssd, group_name)

    groups = eraptor.get_ssd_groups()
    num_of_groups = len(groups)


    if num_of_groups > 0:
        for group in groups:
            print("group: ", group.name)
            all_targets_size = group.get_all_targets_size()

            Gi = 1024 ** 3
            #group = eraptor.get_ssd_group(name)
            total_capacity = group.free_space
            total_capacity_gb = total_capacity/Gi
            all_targets_size = group.get_all_targets_size()
            free_capacity = total_capacity - all_targets_size
            free_capacity_gb = free_capacity/Gi

            # Creating Abstract target from the SSD Group
            print("Creating {} targets from the SSD Group {}".format(no_targets, group.name))
            targetSize =  (free_capacity // no_targets) - Gi # For safer side reducing the size by 1GB
            print("Each target size would be of {} GiB".format(targetSize/Gi))
            print("*************************************************************************************************")

            ssdGroup = toshibaeraptor.SSDGroup(0, group.name, "SSD_GROUP", free_capacity, 0)
            namespace = toshibaeraptor.Namespace("1", targetSize, ns_block_size)

            for t in range(1, no_targets+1):
                target_alias = "tar-{}".format(group.name)
                parent_alias = "perf_testing"
                target = toshibaeraptor.SSDGroupTarget(0, "", target_alias, targetSize, "NVME",parent_alias, ssdGroup)
                target.add_namespace(namespace)
                result = eraptor.create_target(target)
                print("Creating Target {} : Status {}".format(target_alias, result['status']))

    print("*************************************************************************************************")

    # Add ACL to all the targets for the localhost
    print("Connecting all the targets to this initiator")
    print("*************************************************************************************************")

    with open("/etc/nvme/hostnqn") as f:
        host_nqn = f.readline().strip()


    target_names = []
    targets = eraptor.get_targets()
    num_of_targets = len(targets)
    if num_of_targets > 0:
        for target in targets:
            target_names.append(str(target.name))
    init1_target_names = target_names[:len(target_names)//2]
    init2_target_names = target_names[len(target_names)//2:]

    for t in targets:
        if t.name in init1_target_names:
            target_alias = t.alias
            target1 = toshibaeraptor.SSDGroupTarget(0, None, target_alias, 0, None, parent_alias,None)
            acl1 = toshibaeraptor.ACL("WR", True, target1)
            initiator1 = toshibaeraptor.Initiator(host_nqn, localhost_hostname)
            initiator1.add_acl(acl1)
            result = eraptor.connect_host(initiator1)
            print("Adding ACL to target {} to Initiator {}: Status {}".format(target_alias, localhost_hostname, result['status']))
    print("*************************************************************************************************")

    # Add ACL to all the targets for the remote host
    print("Connecting all the targets to the remote initiator")
    print("*************************************************************************************************")

    cmd = "cat /etc/nvme/hostnqn"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    host_nqn = ssh_stdout.read().decode("utf-8").strip()

    for t in targets:
        if t.name in init2_target_names:
            target_alias = t.alias
            target1 = toshibaeraptor.SSDGroupTarget(0, None, target_alias, 0, None, parent_alias,None)
            acl1 = toshibaeraptor.ACL("WR", True, target1)
            initiator2 = toshibaeraptor.Initiator(host_nqn, remote_hostname)
            initiator2.add_acl(acl1)
            result = eraptor.connect_host(initiator2)
            print("Adding ACL to target {} to Initiator {}: Status {}".format(target_alias, remote_hostname, result['status']))

    # Buinding the command to connect the target from initiator using nvme cli

    # 0. Verifying if any device is connected to the initiator if yes, disconnect them first
    # Need to write the function

    # 1. Getting the list of targets
    print("*************************************************************************************************")
    print("Connecting the target from initiator")
    print("*************************************************************************************************")

    target_names = []
    targets = eraptor.get_targets()
    num_of_targets = len(targets)
    if num_of_targets > 0:
        for target in targets:
            target_names.append(str(target.name))

    # # 2. Getting the portal IP
    # portal_ips = []
    # portals = eraptor.get_portals("NVME")
    # num_of_portals = len(portals)
    # if num_of_portals > 0:
    #     for portal in portals:
    #         portal_ips.append(str(portal.ip))

    init1_target_names = target_names[:len(target_names)//2]
    init2_target_names = target_names[len(target_names)//2:]

    # 3. Connecting the targets from initiator using "nvme connect" in the Initiator1(Localhost)

    init1_portals = cfg['initiator1']['portals']
    targets_portal1 = init1_target_names[:len(init1_target_names)//2]
    targets_portal2 = init1_target_names[len(init1_target_names)//2:]
    port = 4420

    nvmecli_cmds.nvme_connect(targets_portal1, init1_portals[0], port)
    nvmecli_cmds.nvme_connect(targets_portal2, init1_portals[1], port)

    # 3. Connecting the targets from initiator using "nvme connect" in the Initiator2(remote host)
    init2_portals = cfg['initiator2']['portals']
    targets_portal1 = init2_target_names[:len(init2_target_names)//2]
    targets_portal2 = init2_target_names[len(init2_target_names)//2:]
    port = 4420

    cmd_template = "nvme connect -n {} -t rdma -a {} -s {}"
    cmds = []
    for t in targets_portal1:
        cmd = cmd_template.format(t, init2_portals[0], port)
        cmds.append(cmd)

    for t in targets_portal2:
        cmd = cmd_template.format(t, init2_portals[1], port)
        cmds.append(cmd)

    for cmd in cmds:
        print("Running this in the remote host : {}".format(cmd))
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
        status = ssh_stderr.read().decode("utf-8").strip()
        if status == "":
            print("Connected")
        if "Failed" in status:
            count = 0
            while count < 10:
                print("Retrying..")
                time.sleep(5)
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
                status = ssh_stderr.read().decode("utf-8").strip()
                if status == "":
                    print("Connected")
                    count = 10
                else:
                    count += 1

        time.sleep(5)

    time.sleep(5)
    print("*************************************************************************************************")

    print("Verifying the list of connected target in the local host")
    output_device = nvmecli_cmds.nvme_list_json()
    print(output_device)

    print("Verifying the list of connected target in the remote host")

    cmd = "nvme list -o json"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    devices = ssh_stdout.read().decode("utf-8").strip()
    devices = json.loads(devices)
    d_list = []
    if devices:
        for d in devices["Devices"]:
            d_list.append(d["DevicePath"])
    print(d_list)


    print("The initiator is now ready for the performance test")
    print("*************************************************************************************************")

def pre_test_tunning_cpu_governing():
    cmd = "lscpu"
    data = nvmecli_cmds.run_command(cmd)
    cpu_count = int(data.split("\n")[3].split(":")[1].strip())
    cmd_set = "echo performance > /sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor"
    cmd_get = "cat /sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor"
    # Check the present scaling_governor
    for c in range(cpu_count):
        cmd1 = cmd_get.format(c)
        p_state = nvmecli_cmds.run_command(cmd1).strip()
        print("Present State of CPU scaling_governor for the CPU {}      :    {}".format(c, p_state))
        print("Changing into Performace")
        cmd2 = cmd_set.format(c)
        os.system(cmd2)
        c_state = nvmecli_cmds.run_command(cmd1).strip()
        print("Currect State of CPU scaling_governor for the CPU {}      :    {}".format(c, c_state))
        print("*************************************************************************************************")

def pre_test_tunning_cpu_governing_remote(ssh):
    cmd = "lscpu"
    data = nvmecli_cmds.run_command_remote(ssh, cmd)
    data = list(data)[0]
    #cpu_count = int(data.split("\n")[3].split(":")[1].strip())
    cpu_count = int(data.split("\n")[3].split(":")[1].strip())

    cmd_set = "echo performance > /sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor"
    cmd_get = "cat /sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor"
    # Check the present scaling_governor
    for c in range(cpu_count):
        cmd1 = cmd_get.format(c)
        p_state, status = nvmecli_cmds.run_command_remote(ssh, cmd1)
        p_state = p_state.strip()

        print("Present State of CPU scaling_governor for the CPU {}      :    {}".format(c, p_state))
        print("Changing into Performace")

        cmd2 = cmd_set.format(c)
        c_state, status = nvmecli_cmds.run_command_remote(ssh, cmd2)
        c_state, status = nvmecli_cmds.run_command_remote(ssh, cmd1)

        c_state = c_state.strip()
        print("Currect State of CPU scaling_governor for the CPU {}      :    {}".format(c, c_state))
        print("*************************************************************************************************")

def pre_test_no_merges():
    device_list = nvmecli_cmds.nvme_list_json()
    device_name = [ d.split("/")[-1] for d in device_list]
    cmd_set = "echo 2 > /sys/block/{}/queue/nomerges"
    cmd_get = "cat /sys/block/{}/queue/nomerges"

    for d in device_name:
        cmd1 = cmd_get.format(d)
        p_state = nvmecli_cmds.run_command(cmd1).strip()
        print("Present nomerges state for the device  {}      :    {}".format(d, p_state))
        print("Changing nomerges to 2")
        cmd2 = cmd_set.format(d)
        os.system(cmd2)
        c_state = nvmecli_cmds.run_command(cmd1).strip()
        print("Currect nomerges state for the device  {}      :    {}".format(d, c_state))
        print("*************************************************************************************************")

def pre_test_no_merges_remote(ssh):
    device_list = nvmecli_cmds.nvme_list_json_remote(ssh)
    device_name = [ d.split("/")[-1] for d in device_list]
    cmd_set = "echo 2 > /sys/block/{}/queue/nomerges"
    cmd_get = "cat /sys/block/{}/queue/nomerges"

    for d in device_name:
        cmd1 = cmd_get.format(d)
        p_state, status = nvmecli_cmds.run_command_remote(ssh, cmd1)
        p_state = p_state.strip()

        print("Present nomerges state for the device  {}      :    {}".format(d, p_state))
        print("Changing nomerges to 2")

        cmd2 = cmd_set.format(d)
        c_state, status = nvmecli_cmds.run_command_remote(ssh, cmd2)
        c_state, status = nvmecli_cmds.run_command_remote(ssh, cmd1)
        c_state = c_state.strip()

        print("Currect nomerges state for the device  {}      :    {}".format(d, c_state))
        print("*************************************************************************************************")

def pre_test_rq_affinity():
    device_list = nvmecli_cmds.nvme_list_json()
    device_name = [ d.split("/")[-1] for d in device_list]
    cmd_set = "echo 2 > /sys/block/{}/queue/rq_affinity"
    cmd_get = "cat /sys/block/{}/queue/rq_affinity"

    for d in device_name:
        cmd1 = cmd_get.format(d)
        p_state = nvmecli_cmds.run_command(cmd1).strip()
        print("Present rq_affinity state for the device  {}      :    {}".format(d, p_state))
        print("Changing nomerges to 2")
        cmd2 = cmd_set.format(d)
        os.system(cmd2)
        c_state = nvmecli_cmds.run_command(cmd1).strip()
        print("Currect rq_affinity state for the device  {}      :    {}".format(d, c_state))
        print("*************************************************************************************************")

def pre_test_rq_affinity_remote(ssh):


    device_list = nvmecli_cmds.nvme_list_json_remote(ssh)
    device_name = [ d.split("/")[-1] for d in device_list]
    cmd_set = "echo 2 > /sys/block/{}/queue/rq_affinity"
    cmd_get = "cat /sys/block/{}/queue/rq_affinity"

    for d in device_name:
        cmd1 = cmd_get.format(d)
        p_state, status = nvmecli_cmds.run_command_remote(ssh, cmd1)
        p_state = p_state.strip()

        print("Present rq_affinity state for the device  {}      :    {}".format(d, p_state))
        print("Changing nomerges to 2")

        cmd2 = cmd_set.format(d)
        c_state, status = nvmecli_cmds.run_command_remote(ssh, cmd2)
        c_state, status = nvmecli_cmds.run_command_remote(ssh, cmd1)
        c_state = c_state.strip()

        print("Currect rq_affinity state for the device  {}      :    {}".format(d, c_state))
        print("*************************************************************************************************")

def main():

    pwd = os.getcwd()
    config = pwd + "/config/config.yml"

    # Reading the config file
    with open(config, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # Reading the Appliance related info(IP, Storage Configuration, etc.)
    remote_host = cfg['initiator2']['ip']
    remote_passwd = cfg['initiator2']['passwd']
    remote_user = cfg['initiator2']['user']
    remote_hostname = cfg['initiator2']['name']

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
    ssh.connect(remote_host, username=remote_user, password=remote_passwd)

    # Setting the configuration
    print("*************************************************************************************************")
    print("Configuring the Initiator and Appliance for the Performance Regression Test")
    setup(cfg, ssh)

    # Setting the CPU Governing in the local and remote host
    print("*************************************************************************************************")
    print("Configuring the pre-test software profiling(cpu_governing) in the local host(Host1)")
    pre_test_tunning_cpu_governing()

    print("*************************************************************************************************")
    print("Configuring the pre-test software profiling(cpu_governing) in the remote host(Host2)")
    pre_test_tunning_cpu_governing_remote(ssh)

    # Setting the no_merges in the local and remote host
    print("*************************************************************************************************")
    print("Configuring the pre-test software profiling(no_merges) in the local host(Host1)")
    pre_test_no_merges()

    print("*************************************************************************************************")
    print("Configuring the pre-test software profiling(no_merges) in the remote host(Host2)")
    pre_test_no_merges_remote(ssh)

    # Setting the rq_affinity in the local and remote host
    print("*************************************************************************************************")
    print("Configuring the pre-test software profiling(rq_affinity) in the local host(Host1)")
    pre_test_rq_affinity()

    print("*************************************************************************************************")
    print("Configuring the pre-test software profiling(rq_affinity) in the remote host(Host2)")
    pre_test_rq_affinity_remote(ssh)

if __name__ == "__main__":
    main()
