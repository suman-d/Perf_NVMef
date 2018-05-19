import subprocess
import time
import json


def run_command(command):
    p = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, err = p.communicate()
    return output.decode("utf-8")

def run_command_remote(ssh, command):
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
    status = ssh_stderr.read().decode("utf-8").strip()
    output = ssh_stdout.read().decode("utf-8")

    return output, status

def nvme_connect(target_names, portal_ip, port):
    '''It takes the list of targets in the form of list and connect in
       the initiator with the portal_ip and port
    '''
    cmd_template = "nvme connect -n {} -t rdma -a {} -s {}"

    for t in target_names:
        cmd = cmd_template.format(t, portal_ip, port)
        print("Connecting Target: {}".format(t))
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        output, err = p.communicate()
        if err is None:
            print("Connected")
        else:
            count = 0
            while count < 10:
                print("Retrying..")
                time.sleep(5)
                p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
                output, err = p.communicate()
                if err is None:
                    print("Connected")
                    count = 10
                else:
                    count += 1
        time.sleep(5)

def disconnect_targets():
    # 0. Verifying if any device is connected to the initiator if yes, disconnect them first

    output = nvme_list()
    _, devices = nvme_dev(output)
    cmd_template = "nvme disconnect -d {}"

    if devices:
        b_devices = devices
        for b in b_devices:
            cmd = cmd_template.format(b)
            print("Disconnecting Target: {}".format(b))
            p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
            output, err = p.communicate()
        time.sleep(5)
    else:
        print("No target connected with the initiator")
    print("*************************************************************************************************")

def nvme_dev(output):
    output = output.strip().split("\n")
    output = [i.strip() for i in output]
    output = output[2::]

    c_device_list = []
    devices = {}

    if output:
        b_device_list = [ d.split()[0] for d in output]

        for i in b_device_list:
            c_device = i.rsplit("n", 1).pop(0)
            c_device_list.append(c_device)
            if c_device in devices:
                devices[c_device].append(i)
            else:
                devices[c_device] = [i]

    return devices, c_device_list

def nvme_list():
    p = subprocess.Popen(["nvme", "list"], stdout=subprocess.PIPE)
    output, err = p.communicate()

    return output.decode("utf-8")

def nvme_smart_log(devices):

    _, devices = nvme_dev(devices)
    test_stats = {}
    for d in devices:
        cmd = "nvme smart-log {}".format(d)
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        output, err = p.communicate()
        test_stats[d] = output.decode("utf-8")

    return test_stats

def smart_getter(devices):
    test_stats = {}
    pram = ['data_units_read', 'data_units_written', 'host_read_commands', 'host_write_commands', 'media_errors', 'num_err_log_entries']
    total_stats = dict.fromkeys(pram, 0)

    for d in devices:
        raw = smart_filer(devices[d])
        for i in pram:
            raw[i] = int(raw[i].replace(",", ""))
            total_stats[i] += raw[i]
        test_stats[d] = raw

    return total_stats, test_stats

def smart_filer(smart_out):
    final_data = {}
    data = smart_out.strip().split("\n")

    f_line = data.pop(0)
    _, final_data["namespace-id"] = f_line.split("namespace-id")
    data.append(_)

    for stats in data:
        k, v = stats.split(":")
        final_data[k.strip()] = v.strip()

    return final_data

def nvme_error_log(devices):
    _, devices = nvme_dev(devices)
    test_err_logs = {}
    for d in devices:
        cmd = "nvme error-log {} -e 1 -o json".format(d)
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        output, err = p.communicate()
        o = json.loads(output.decode("utf-8"))
        test_err_logs[d] = o

    return test_err_logs

def nvme_list_json():
    cmd = "nvme list -o json"
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, err = p.communicate()
    output = json.loads(o.decode("utf-8"))
    device_list = []
    for d in output["Devices"]:
        device_list.append(d["DevicePath"])

    return device_list

def nvme_list_json_remote(ssh):
    cmd = "nvme list -o json"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    devices = ssh_stdout.read().decode("utf-8").strip()
    devices = json.loads(devices)
    d_list = []
    if devices:
        for d in devices["Devices"]:
            d_list.append(d["DevicePath"])

    return d_list
