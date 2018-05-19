
'''This is part of Perf_NVMef Tool Kit
   This tool merge all the test data from host1, host2, appliance with CPU, MEM, FIO test results\
   All in one CSV file called "final.csv" which can be later used for analysis across different builds'''

# Author : Suman Debnath
# E-Mail : suman.debnath@toshiba-tsip.com
# Last Update: 13-March-2018
# Version: 1.1


import os
import glob
import shutil
import time
import sys
import argparse
import json
from collections import OrderedDict
import pandas as pd
import datetime

import warnings
warnings.filterwarnings('ignore')


def ParseArgs():
    """Parse command line options into globals."""
    global result_folder

    parser = argparse.ArgumentParser(
                 formatter_class=argparse.RawDescriptionHelpFormatter,
    description="This is a part of KumoScale Performance QA Regression Testing tool. \n" \
                "The module will will move all the required file which would be used \n" \
                "for the data analysis and reporting, this should be used once a test \n" \
                "run is complete",
    epilog="""
    Requirements:\n
    * Already completed a test run using "nvmef_perf" tool and the "Result" folder is available
    \n\n
    """)
    parser.add_argument("--resultFolder", "-f", dest = "result_folder",
        help="Provide the full path of the Test Result Folder", required=True)

    args = parser.parse_args()

    result_folder = args.result_folder

def csv_to_df(csv_file):

    df = pd.read_csv(csv_file)
    df["Timestamp"] = pd.to_datetime(df.Timestamp, format="%Y-%m-%d_%H-%M-%S")
    df["Stat_Start_Time"] = df["Timestamp"] - datetime.timedelta(seconds=110)
    df["Stat_End_Time"] = df["Timestamp"] - datetime.timedelta(seconds=10)
    df.index = pd.RangeIndex(1, len(df.index)+1)

    df.columns = [i.strip() for i in df.columns]

    return df

def merg_df(df1, df2):

    frames = [df1, df2]
    merg = pd.concat(frames, axis=0)
    merg.index = pd.RangeIndex(1, len(merg.index)+1)

    return merg

def combine_df(df1, df2):

    combine = df1.copy()
    #row_index = df1.index

    prams_avg = ["Read Latency (us)", "Write Latency (us)"]
    prams_sum = ["IOPS", "Bandwidth (MB/s)"]
    for p in prams_sum:
        combine[p] = combine[p] + df2[p]
    for p in prams_avg:
        combine[p] = (combine[p] + df2[p]) / 2

    combine["Host2_CPU_Utilization"] = df2["Host2_CPU_Utilization"]
    combine["Host2_Memory_Utilization"] = df2["Host2_Memory_Utilization"]

    return combine

def df_to_csv(df, file_name):

    df.to_csv(file_name,index=False)
    file_path = os.path.abspath(file_name)

    return file_path

def json_to_df(json_file):

    df_stat = pd.read_json(json_file, orient='index')
    df_stat.columns = ["CPU_Utilization", "Memory_Utilization"]
    df_stat["Timestamp"] = pd.to_datetime(df_stat.index, format="%Y-%m-%d_%H-%M-%S")
    #df_stat.index = df_stat["Timestamp"]
    df_stat.index = pd.RangeIndex(1, len(df_stat.index)+1)


    return df_stat

def file_scanner(list_files):

    global host1_tput_file, host1_lat_file, host2_tput_file, stat_appliance_lat_file
    global stat_appliance_tput_file, stat_host1_lat_file, stat_host1_tput_file, stat_host2_tput_file

    host1_files = []

    for file in list_files:
        _file = os.path.basename(file)
        if _file.startswith("ezfio_tests_"):
            if "host1" in _file.split("_"):
                host1_files.append(file)
            else:
                host2_tput_file = file
        elif _file.startswith("lat_appliance"):
            stat_appliance_lat_file = file
        elif _file.startswith("tput_appliance"):
            stat_appliance_tput_file = file
        elif _file.startswith("lat_host1"):
            stat_host1_lat_file = file
        elif _file.startswith("tput_host1"):
            stat_host1_tput_file = file
        elif _file.startswith("tput_host2"):
            stat_host2_tput_file = file

    _host1_files = {}
    for file in host1_files:
        _file = os.path.basename(file)
        _t = _file.split("_")[2].split("GB")[0]
        _host1_files[int(_t)] = file

    lat, tput = sorted(_host1_files)
    host1_tput_file = _host1_files[tput]
    host1_lat_file = _host1_files[lat]

def cpu_mem_avg_calculator(stat_df, start_time, end_time):

    c_util, m_util = stat_df[(stat_df["Timestamp"] >= start_time) & (stat_df["Timestamp"] <= end_time)].mean()
    return int(c_util), int(m_util)

def add_cpu_mem_stat(master_df, stat_df, host_name):

    cpu_util = []
    mem_util = []
    for _, row in master_df.iterrows():
        start, end = row["Stat_Start_Time"], row["Stat_End_Time"]
        c, m = cpu_mem_avg_calculator(stat_df, start, end)
        cpu_util.append(c)
        mem_util.append(m)

    cpu_col_name = host_name + "_CPU_Utilization"
    mem_col_name = host_name + "_Memory_Utilization"
    master_df[cpu_col_name] = cpu_util
    master_df[mem_col_name] = mem_util

    return  master_df

result_folder = ""

host1_tput_file = ""
host1_lat_file = ""
host2_tput_file = ""
stat_appliance_lat_file = ""
stat_appliance_tput_file = ""
stat_host1_lat_file = ""
stat_host1_tput_file = ""
stat_host2_tput_file = ""



if __name__ == "__main__":

    ParseArgs()

    # Creating a new folder called "post_run" under the same "result_folder"
    new_folder_path = os.path.join(result_folder, "post_run")
    os.system("rm -rf {}".format(new_folder_path))

    #time.sleep(2)
    os.makedirs(new_folder_path)

    # Filtering the required files from Host1, Host2 and Appliance
    files_to_copy = []
    for root, dirs, files in os.walk(result_folder, topdown=False):
        for name in files:
            if name.startswith("ezfio_tests_") or name.startswith("host") or name.startswith("lat_") or name.startswith("tput_"):
                files_to_copy.append((os.path.join(root, name)))

    # Copying all the files to "post_run" folder
    for f in files_to_copy:
        shutil.copy(f, new_folder_path)

    # Printing the path of the new_folder and its file contents
    print("*"*120)
    print("This is the folder path which contains all the files :  {}".format(new_folder_path))
    print("*"*120)

    print("Here are the files: ")
    print("*"*120)

    list_files = []
    for f in (os.listdir(new_folder_path)):
        file_path = os.path.join(new_folder_path, f)
        print(file_path)
        list_files.append(file_path)

    print("*"*120)
    print("Computing the Data Collection for IOPS, Throughput, Latency, CPU/Mem Utilization for Host1, Host2 and Appliance")
    print("*"*120)

    # Identifying the test files for Host1, Host2 and Appliance

    file_scanner(list_files)

    # Loading the all the CSV files to DataFrame

    # Loading IO,TPUT and Latency Test Data for Host1
    df_host1_tput = csv_to_df(host1_tput_file)
    df_host1_lat = csv_to_df(host1_lat_file)

    # Loading IO,TPUT Test Data for Host2
    df_host2_tput = csv_to_df(host2_tput_file)

    # Loading the CPU and Mem stats for Host1
    df_stat_host1_lat = json_to_df(stat_host1_lat_file)
    df_stat_host1_tput = json_to_df(stat_host1_tput_file)

    # Loading the CPU and Mem stats for Host2
    df_stat_host2_tput = json_to_df(stat_host2_tput_file)

    # Loading the CPU and Mem stats for Appliance
    df_stat_appliance_lat = json_to_df(stat_appliance_lat_file)
    df_stat_appliance_tput = json_to_df(stat_appliance_tput_file)

    # Calculating the CPU and Memory Utilization and adding to the DataFrame

    df_host1_lat = add_cpu_mem_stat(df_host1_lat, df_stat_host1_lat, "Host1")
    df_host1_tput = add_cpu_mem_stat(df_host1_tput, df_stat_host1_tput, "Host1")
    df_host1_lat = add_cpu_mem_stat(df_host1_lat, df_stat_appliance_lat, "Appliance")
    df_host1_tput = add_cpu_mem_stat(df_host1_tput, df_stat_appliance_tput, "Appliance")
    df_host2_tput = add_cpu_mem_stat(df_host2_tput, df_stat_host2_tput, "Host2")

    # Combining Host1 and Host2 Results after CPU and Memory Calculation

    df = combine_df(df1=df_host1_tput, df2=df_host2_tput)

    # Adding the Latency Results to the final DataFrame

    df_final = merg_df(df, df_host1_lat)

    # Saving the final DataFrame to a CSV File

    final_csv_file_path = result_folder + "/final.csv"
    df_to_csv(df_final, final_csv_file_path)

    # Copying the same file inside the "post_run" folder as well

    shutil.copy(final_csv_file_path, new_folder_path)

    # Printing the path of the final.csv
    print("Here is the path of the final CSV :")
    print(final_csv_file_path)
    print("*"*120)
