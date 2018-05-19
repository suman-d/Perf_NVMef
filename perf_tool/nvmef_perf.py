'''This is part of Perf_NVMef Tool Kit
   This is the main tool, which does the following:
    - Prepare the Appliance for the test
    - Prepare the hosts for the test
    - Connects the targets to all the hosts
    - Starts all the tests
    - Monitor CPU, MEM, IO, etc for both the hosts and appliance
    - Generates the result folder at the end

   This tool will generate charts and start a local webserver with performance dashboard
   This will also same all the seperate charts in HTML'''

# Author : Suman Debnath
# E-Mail : suman.debnath@toshiba-tsip.com
# Last Update: 18-March-2018
# Version: 1.2


import yaml
import os
import sys
import random
import socket
import time
import paramiko
import json
import subprocess
import argparse
import prepare
import shutil
import datetime
import psutil
import datetime
from threading import Thread
from lib import toshibaeraptor
from lib import nvmecli_cmds
from lib import monitor_local_initiator
from pprint import pprint as pp
from subprocess import Popen, PIPE, CalledProcessError

def ParseArgs():
    """Parse command line options into globals."""
    global testMode, targetType
    parser = argparse.ArgumentParser(
                 formatter_class=argparse.RawDescriptionHelpFormatter,
    description="A KumoScale Performance QA Regression Testing tool. " \
                "The tool will generate IO with different workload based on the " \
                "Performance QA Regression Test Plan",
    epilog="""
    Requirements:\n
    * Root access (log in as root, or sudo {prog})
    * No filesytems or data on target device
    * FIO IO tester (available https://github.com/axboe/fio)
    * Nvmecli to be installed in all the hosts
    * Python package "psutil" should be installed in all the systems
    * Firewall should be disabled
    * Proxy should be not be enabled
    \n\n
    """)
    parser.add_argument("--testMode", "-m", dest = "testMode",
        help="Test type('baseline' or 'build'). Default = 'build'", default="build", required=False)
    # parser.add_argument("--kumoscaleBuild", "-b", dest="kumoscaleBuild",
    #     help="KumoScale Build Number. Default = 'dryrun'", default="dryrun",
    #     type=str, required=False)
    parser.add_argument("--targetType", "-t", dest="targetType",
        help="Target type('abstract' or 'transparenet'). Default = 'abstract'", default="abstract", required=False)

    args = parser.parse_args()

    testMode = args.testMode
    # kumoscaleBuild = args.kumoscaleBuild
    targetType = args.targetType

def Run(cmd):
    """Run a cmd[], return the exit code, stdout, and stderr."""
    proc=subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.read()
    err = proc.stderr.read()
    code = proc.wait()
    return code, out, err

def Run2(cmd):
    """Run a cmd[], return the exit code, stdout, and stderr."""
    p = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL)
    return p


def SetupFiles():

    global testMode, kumoscaleBuild, targetType

    # Check for the Result folder
    directory = "/root/KumoScale_Perf_QA_Results"

    if not os.path.exists(directory):
        os.makedirs(directory)

    # Datestamp for run output files
    ds = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # The unique suffix we generate for all output files
    suffix  = str(testMode) + "_"
    suffix += str(targetType) + "_"
    suffix += str(kumoscaleBuild) + "_" + ds

    test_dir = directory + "/Results_" + suffix
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    os.makedirs(test_dir)

    test_dir_local = test_dir + "/local"
    test_dir_remote = test_dir + "/remote"
    test_dir_appliance = test_dir + "/appliance"
    os.makedirs(test_dir_local)
    os.makedirs(test_dir_remote)
    os.makedirs(test_dir_appliance)

    return test_dir, test_dir_local, test_dir_remote, test_dir_appliance

def JobWrapper_Precondition_Local(cmd):
    p = Run2(cmd)

def JobWrapper_Precondition_Remote(ssh, cmd):
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)


def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return hours, minutes, seconds


# Setting the global variables
testMode = ""
kumoscaleBuild = ""
targetType = ""


if __name__ == "__main__":

    ParseArgs()
    prepare.main()

    # Reading the config file
    pwd = os.getcwd()
    config = pwd + "/config/config.yml"
    with open(config, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # Reading the Appliance related info(IP, Storage Configuration, etc.)
    remote_host = cfg['initiator2']['ip']
    remote_passwd = cfg['initiator2']['passwd']
    remote_user = cfg['initiator2']['user']
    remote_hostname = cfg['initiator2']['name']
    appliance_ip = cfg['appliance']['ip']
    appliance_user = cfg['appliance']['user']
    appliance_passwd = cfg['appliance']['passwd']

    # Get the KumoScale Version
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
    ssh.connect(appliance_ip, username=appliance_user, password=appliance_passwd)

    print("*"*100)
    print("Fetching the KumoScale Appliance Version")
    print("*"*100)

    cmd = "cat /usr/local/ERaptor/Version.txt"

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    kumoscaleBuild = ssh_stdout.read().decode("utf-8").strip()

    time.sleep(2)

    test_dir, test_dir_local, test_dir_remote, test_dir_appliance = SetupFiles()

    # Making a remote connection object
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
    ssh.connect(remote_host, username=remote_user, password=remote_passwd)

    # Copy all the required files from local host to remote host
    print("*"*100)
    print("Copying all the files and folders for from local host to remote host")
    print("*"*100)

    basedir = os.getcwd()

    cmd = "rm -rf {}/*".format(basedir)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)

    time.sleep(5)

    cmd = "rm -rf /root/details_*"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)

    time.sleep(5)

    cmd = "rm -rf /root/ezfio_results*"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)

    time.sleep(5)

    cmd = "scp -r * {}:{}".format(remote_host, basedir)
    print(cmd)
    os.system(cmd)

    # List of all the devices

    local_devices = nvmecli_cmds.nvme_list_json()
    host1_devices = ":".join(local_devices)

    # List of remote devices
    remote_devices = nvmecli_cmds.nvme_list_json_remote(ssh)
    host2_devices = ":".join(local_devices)


    # Start Preconditioning
    # print("*"*100)
    # print("Starting Sequential Preconditioning on the Local and Remote Host")
    # print("*"*100)
    #
    # cmd_local = "/usr/bin/python " + basedir + "/ezfio/precondition.py -d {} --yes".format(host1_devices)
    # cmd_remote = "/usr/bin/python " + basedir + "/ezfio/precondition.py -d {} --yes".format(host2_devices)
    #
    # t_precon_local = Thread(target=JobWrapper_Precondition_Local, args=(cmd_local,))
    # t_precon_remote = Thread(target=JobWrapper_Precondition_Remote, args=(ssh, cmd_remote))
    #
    # start_time = datetime.datetime.now()
    # # 1. Start 1st thread to run in the local host
    # t_precon_local.start()
    # print ("Precondition Started in Host 1")
    # # 2. Start 2nd thread to run in the remote host
    # t_precon_remote.start()
    # print("Precondition Started in Host 2")
    # print("*"*100)
    # print("Waiting for the first poll after 60 seconds")
    # print("*"*100)
    # # Waiting for 60 seconds before starting the first polling
    # time.sleep(60)
    #
    # # Wait for the precondition to get over in the local system
    # fio_process_check = [p.info['pid'] for p in psutil.process_iter(attrs=['pid', 'name']) if 'fio' in p.info['name']]
    #
    # while bool(fio_process_check) == True:
    #     print("Precondition is going on Host1 and Host2 (Next poll after 60 seconds)")
    #     time.sleep(60)
    #     fio_process_check = [p.info['pid'] for p in psutil.process_iter(attrs=['pid', 'name']) if 'fio' in p.info['name']]
    #
    #
    # end_time_host1 = datetime.datetime.now()
    # print("*"*100)
    # print("Precondition is over in Host1")
    # print("*"*100)
    #
    #
    # cmd = '''python -c "import psutil; fio_process_check = [p.info['pid'] for p in psutil.process_iter(attrs=['pid', 'name']) if 'fio' in p.info['name']]; print(fio_process_check)"'''
    #
    # ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    # fio_process_check = ssh_stdout.read().decode("utf-8").strip()
    #
    # while bool(fio_process_check) == True:
    #     print("Precondition is going on Host2 (Poll every after 60 seconds)")
    #     time.sleep(60)
    #     ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    #     fio_process_check = ssh_stdout.read().decode("utf-8").strip()
    #     fio_process_check = json.loads(fio_process_check)
    #
    # end_time_host2 = datetime.datetime.now()
    # print("*"*100)
    # print("Precondition is over in Host2")
    # print("*"*100)
    #
    # duration_preconditio_host1 = end_time_host1 - start_time
    # pre_host1_duration = round(duration_preconditio_host1.seconds /60, 2)
    #
    # duration_preconditio_host2 = end_time_host2 - start_time
    # pre_host2_duration = round(duration_preconditio_host2.seconds /60, 2)
    #
    # print("Precondition in Host1 took roughly {} minutes".format(pre_host1_duration))
    # print("Precondition in Host2 took roughly {} minutes".format(pre_host2_duration))
    # print("*"*100)
    # print("Preconditioning for all the targets are over in both the hosts (Host1 and Host2)")
    # print("*"*100)
    # print("Sleeping for 300 seconds")
    # time.sleep(300)
    # print("*"*100)

    print("Starting the Testing Suite")
    print("*"*100)

    pre_stat_time = datetime.datetime.now()
    # duration_monitor in "Seconds"
    duration_monitor = 60 * 56 * 2  # 54 Tests each runs for 2 mins, collecting the stats for 4 mins more
    post_stat_time = pre_stat_time + datetime.timedelta(seconds=duration_monitor)

    print("Starting collecting the CPU and Memory Stats from both the Hosts and Appliance")
    print("*"*100)


    cmd = "python " + basedir + "/lib/monitor_local_initiator.py {} {}".format(duration_monitor, "tput")
    #cmd_appliance = "python " + basedir + "/lib/monitor_appliance.py {} {} {}".format(appliance_ip, duration_monitor, test_dir_appliance)
    cmd_appliance = "python " + basedir + "/lib/monitor_appliance.py {} {} {} {}".format("tput", test_dir_appliance, appliance_ip, duration_monitor)

    t_monitor_local = Thread(target=JobWrapper_Precondition_Local, args=(cmd,))
    t_monitor_remote = Thread(target=JobWrapper_Precondition_Remote, args=(ssh, cmd))
    t_monitor_appliance = Thread(target=JobWrapper_Precondition_Local, args=(cmd_appliance,))

    # 1. Start 1st thread to start monitoring the local host
    t_monitor_local.start()
    # 2. Start 2nd thread to start monitoring the remote host
    t_monitor_remote.start()
    # 3. Start 3rd thread to start monitoring in applaince
    t_monitor_appliance.start()

    # Starting IO from both the hosts

    print("*"*100)

    cmd_local = "/usr/bin/python " + basedir + "/ezfio/my_ezfio.py -d {} --yes".format(host1_devices)
    cmd_remote = "/usr/bin/python " + basedir + "/ezfio/my_ezfio.py -d {} --yes".format(host2_devices)

    t_bwio_local = Thread(target=JobWrapper_Precondition_Local, args=(cmd_local,))
    t_bwio_remote = Thread(target=JobWrapper_Precondition_Remote, args=(ssh, cmd_remote))

    # 1. Start 1st thread to run in the local host
    print("Starting the IO in Host1")
    t_bwio_local.start()

    # 2. Start 2nd thread to run in the remote host
    t_bwio_remote.start()
    print("Starting the IO in Host2")

    while datetime.datetime.now() < post_stat_time:
        print("IO and Bandwidth Tests are running now ....")
        td = post_stat_time - datetime.datetime.now()
        hours, minutes, seconds = convert_timedelta(td)
        print('{} hours, {} minutes and {} seconds remaining for the test to complete'.format(hours, minutes, seconds))
        time.sleep(60*10)


    # Adding the latency test
    print("*"*100)
    print("All the test for Bandwidth and IOPS is over")
    print("*"*100)

    pre_stat_time = datetime.datetime.now()
    # duration_monitor in "Seconds"
    duration_monitor = 60 * 60 * 2  # Running the monitoring for 2 hours (which includes precondition time as well)
    post_stat_time = pre_stat_time + datetime.timedelta(seconds=duration_monitor)

    print("Starting collecting the CPU and Memory Stats from both the Hosts and Appliance")
    print("*"*100)

    cmd = "python " + basedir + "/lib/monitor_local_initiator.py {} {}".format(duration_monitor, "lat")
    #cmd_appliance = "python " + basedir + "/lib/monitor_appliance.py {} {} {}".format(appliance_ip, duration_monitor, test_dir_appliance)
    cmd_appliance = "python " + basedir + "/lib/monitor_appliance.py {} {} {} {}".format("lat", test_dir_appliance, appliance_ip, duration_monitor)

    t_monitor_local = Thread(target=JobWrapper_Precondition_Local, args=(cmd,))
    t_monitor_appliance = Thread(target=JobWrapper_Precondition_Local, args=(cmd_appliance,))

    # 1. Start 1st thread to start monitoring the local host
    t_monitor_local.start()
    # 2. Start 2nd thread to start monitoring in applaince
    t_monitor_appliance.start()


    print("Starting the latency tests ONLY on host1")
    print("*"*100)

    tar_lat = host1_devices.split(":")[0]
    cmd_local_lat = "/usr/bin/python " + basedir + "/ezfio/latency.py -d {} --yes".format(tar_lat)

    t_lat_local = Thread(target=JobWrapper_Precondition_Local, args=(cmd_local_lat,))
    t_lat_local.start()

    while datetime.datetime.now() < post_stat_time:
        print("Latency Test are running now ....")
        td = post_stat_time - datetime.datetime.now()
        hours, minutes, seconds = convert_timedelta(td)
        print('{} hours, {} minutes and {} seconds remaining for the test to complete'.format(hours, minutes, seconds))
        time.sleep(60*10)

    # End of latency test

    print("*"*100)
    print("All the tests got over, sleeping for 10mins before start moving the result files")
    print("*"*100)
    time.sleep(60*10)


    print("Now moving the files to the result folder {}".format(test_dir))
    print("*"*100)

    # Transfer the test results for Host1
    destination_path = test_dir_local
    source_file_names = [ os.path.abspath(f) for f in os.listdir(basedir) if f.startswith("details_") or f.startswith("ezfio_") or f.startswith("tput_") or f.startswith("lat_")]

    # For debugging
    pp(source_file_names)

    for f in source_file_names:
        cmd = "mv {} {}".format(f, destination_path)

        os.system(cmd)
        time.sleep(120)

    # # Transfer the test results for Appliance
    # destination_path = test_dir_appliance
    # source_file_names = [ os.path.abspath(f) for f in os.listdir(basedir) if f.startswith("appliance") ]
    #
    # # For debugging
    # pp(os.listdir(basedir))
    # pp(source_file_names)
    #
    # time.sleep(60*10)
    # for f in source_file_names:
    #     cmd = "mv {} {}".format(f, destination_path)
    #     # For debugging
    #     pp(cmd)
    #
    #     os.system(cmd)
    #     time.sleep(120)

    # Transfer the test results for Host2
    destination_path = test_dir_remote
    cmd = "python -c " + '"import os, socket; source_file_names = [ os.path.abspath(f) for f in os.listdir(\'/root\') if f.startswith(\'details_\') or f.startswith(\'ezfio_\') or f.startswith(\'tput_\') or f.startswith(\'lat_\')]; print(source_file_names)"'

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    source_file_names = ssh_stdout.read().decode("utf-8").strip()
    source_file_names = source_file_names.replace("'", "\"")
    source_file_names = json.loads(source_file_names)

    for f in source_file_names:
        cmd = "scp -r root@{}:{} {}".format(remote_host, f, destination_path)
        os.system(cmd)
        time.sleep(120)
        cmd_remote = "rm -rf {}".format(f)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_remote)
