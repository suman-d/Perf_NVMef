import os
import glob
import shutil
import time
import sys
import argparse
import pandas as pd
import numpy as np
import datetime
from collections import OrderedDict

import warnings
warnings.filterwarnings('ignore')


def ParseArgs():
    """Parse command line options into globals."""
    global result_folder

    parser = argparse.ArgumentParser(
                 formatter_class=argparse.RawDescriptionHelpFormatter,
    description="This is a part of KumoScale Performance QA Regression Testing tool. \n" \
                "The module will create a new baseline based on 5 or more baseline  \n" \
                "test runs with 95 percentile",

    epilog="""
    Requirements:\n
    * Already completed 5 or more test run using "nvmef_perf" tool for the baseline \n"
    and the "Results_baseline" folders are available in this present working dir
    \n\n
    """)
    parser.add_argument("--resultFolder", "-f", dest = "result_folder",
        help="Provide the full path of all the Baseline Test Result Folders seperated by SPACE", required=False,
        default=" ".join(result_folder))

    args = parser.parse_args()
    result_folder = args.result_folder.split()


def results_df(folders):

    baseline_runs = []
    num = 1
    for f in folders:
        f_name = os.path.basename(f)
        result_file = os.path.join(f, "final.csv")
        df = pd.read_csv(result_file)
        df.fillna(0, inplace=True)
        baseline_runs.append(df)

    return baseline_runs

def get_baseline_df(all_runs):

    cols = ["Appliance_CPU_Utilization",
        "Appliance_Memory_Utilization",
        "Host1_CPU_Utilization",
        "Host2_CPU_Utilization",
        "Host1_Memory_Utilization",
        "Host2_Memory_Utilization",
        "IOPS",
        "Bandwidth (MB/s)",
        "Read Latency (us)",
        "Write Latency (us)"
        ]

    df_baseline_final = all_runs[0].copy()
    for c in cols:
        df_baseline_final[c] = np.percentile([df[c] for df in all_runs], q=99, axis=0)

    return df_baseline_final

def df_to_csv(df, file_name):

    df.to_csv(file_name,index=False)
    file_path = os.path.abspath(file_name)

    return file_path



# Starts Here
pwd= os.getcwd()
result_folder = [ os.path.join(pwd, f) for f in os.listdir(os.getcwd()) if os.path.isdir(f) and "baseline" in f.lower()]
baseline_folder_name = os.path.basename(max(result_folder))
baseline_folder_name = "_".join(baseline_folder_name.split("_")[:-2])
new_folder_path = os.path.join(pwd, baseline_folder_name)


if __name__ == "__main__":

    ParseArgs()
    # Creating DF for all the result folders using the "final.csv" inside every folder
    all_runs = results_df(result_folder)
    df_baseline_final = get_baseline_df(all_runs)

    # Creating a new baseline folder
    os.mkdir(new_folder_path)

    # Saving the df to this new baseline folder in a csv called "final.csv"
    final_csv_file_path = new_folder_path + "/final.csv"
    summary_file_path = new_folder_path + "/summary.txt"
    baseline_path = df_to_csv(df_baseline_final, final_csv_file_path)

    # Writing a summary file to note which are the result folder was used for this baseline calculation
    with open(summary_file_path , 'w') as fp:
        fp.write("\n".join(result_folder))

    print("Here is the final baseline file path : {}".format(baseline_path))
