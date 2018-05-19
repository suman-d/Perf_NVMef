
'''This is part of Perf_NVMef Tool Kit
   This tool will calculate the regression between the latest and baseline build and \
   will generate a Executive Summary
   This will also same all the seperate charts in HTML'''

# Author : Suman Debnath
# E-Mail : suman.debnath@toshiba-tsip.com
# Last Update: 13-March-2018
# Version: 1.1


import datetime
from collections import OrderedDict
from pprint import pprint as pp

# Not needed now
def ParseArgs():
    """Parse command line options into globals."""
    global result_folders

    parser = argparse.ArgumentParser(
                 formatter_class=argparse.RawDescriptionHelpFormatter,
    description="This is a part of KumoScale Performance QA Regression Testing tool. \n" \
                "The module will generate Executive Summary of the results \n",
    epilog="""
    Requirements:\n
    * Already completed a test run using "nvmef_perf" tool and the "Result" folder is available
    * Already completed running "post_test_data_collector" tool for all the result folders
    * All the result folder are located in the present working directory, which this script is present
    \n\n
    """)
    parser.add_argument("--resultFolders", "-f", dest = "result_folders",
        help="Provide Test Result Folder Seperated by space", required=True)

    args = parser.parse_args()

    result_folders = args.result_folders.split()

def bw_reg_chk(test_name, df_base, df_current, base_version, latest_version):
    global exe_summary, regression_percent

    df = df_current.copy()
    df["Regression_Percent"] = (df_current["Bandwidth (MB/s)"] - df_base["Bandwidth (MB/s)"]) / df_base[
        "Bandwidth (MB/s)"] * 100

    df_regression = df[df["Regression_Percent"] < regression_percent]

    if len(df_regression.index) == 0:
        pass

    else:
        for index, row in df_regression.iterrows():
            bs = row["Block Size"]
            reg_p = int(row["Regression_Percent"])
            msg = "{}% regression is observed for the test '{}' for the Block_Size of {}".format(abs(reg_p), test_name,
                                                                                                 bs)
            exe_summary["Bandwidth"].append(msg)

    return df_regression

def iops_qd_reg_chk(test_name, df_base, df_current, base_version, latest_version):
    global exe_summary, regression_percent

    df = df_current.copy()
    df["Regression_Percent"] = (df_current["IOPS"] - df_base["IOPS"]) / df_base["IOPS"] * 100

    df_regression = df[df["Regression_Percent"] < regression_percent]

    if len(df_regression.index) == 0:
        # exe_summary["IOPS"].append("No regression for the test '{}'".format(test_name))
        pass

    else:
        for index, row in df_regression.iterrows():
            thread = row["Threads"]
            reg_p = int(row["Regression_Percent"])
            msg = "{}% regression is observed for the test '{}' with '{}' Threads ".format(abs(reg_p), test_name,
                                                                                           thread)
            exe_summary["IOPS"].append(msg)

    return df_regression

def iops_bs_reg_chk(test_name, df_base, df_current, base_version, latest_version):

    global exe_summary, regression_percent

    df = df_current.copy()
    df["Regression_Percent"] = (df_current["IOPS"] - df_base["IOPS"]) / df_base["IOPS"] * 100

    df_regression = df[df["Regression_Percent"] < regression_percent]

    if len(df_regression.index) == 0:
        #exe_summary["IOPS"].append("No regression for the test '{}'".format(test_name))
        pass

    else:
        for index, row in df_regression.iterrows():
            bs = row["Block Size"]
            reg_p = int(row["Regression_Percent"])
            msg = "{}% regression is observed for the test '{}' for the Block_Size of {}".format(abs(reg_p), test_name,bs)
            exe_summary["IOPS"].append(msg)

    return df_regression

def lat_reg_chk(test_name, df_base, df_current, base_version, latest_version):
    global exe_summary, regression_percent

    if "write" in test_name.lower():
        col = "Write Latency (us)"
    else:
        col = "Read Latency (us)"

    df = df_current.copy()
    df["Regression_Percent"] = (df_current[col] - df_base[col]) / df_base[col] * 100

    df_regression = df[df["Regression_Percent"] < regression_percent]

    if len(df_regression.index) == 0:
        # exe_summary["Latency"].append("No regression for the test '{}'".format(test_name))
        pass

    else:
        for index, row in df_regression.iterrows():
            threads = row["Threads"]
            reg_p = int(row["Regression_Percent"])
            msg = "{}% regression is observed for the test '{}' with '{}' Threads ".format(abs(reg_p), test_name,
                                                                                           threads)
            exe_summary["Latency"].append(msg)

    return df_regression

def gen_summary(results):
    global exe_summary

    for data in results:
        if data.endswith("_BW"):
            test_name = data.split("_")[0]
            arg = test_name, results[data][1], results[data][2], results[data][5], results[data][6]
            bw_reg_chk(*arg)

        elif data.endswith("_IOPS"):
            test_name = data.split("_")[0]
            arg = test_name, results[data][1], results[data][2], results[data][5], results[data][6]
            if "block size" in data.lower():
                iops_bs_reg_chk(*arg)
            else:
                iops_qd_reg_chk(*arg)

        else:
            test_name = data.split("_")[0]
            arg = test_name, results[data][1], results[data][2], results[data][5], results[data][6]
            lat_reg_chk(*arg)

        exe_summary["Latest Version"] = arg[-1]
        exe_summary["Baseline Version"] = arg[-2]
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")
        exe_summary["Date"] = now_str


    for data in exe_summary:
        if len(exe_summary[data]) == 0:
            exe_summary[data] = ["No Regression Found"]

    summary = exe_summary

    return summary

regression_percent = -10
exe_summary = OrderedDict({"Bandwidth": [],
                           "Latency": [],
                           "IOPS": [],
                           "Latest Version": "",
                           "Baseline Version": "",
                           "Date": ""})

if __name__ == "__main__":
    pass

    # ParseArgs()
    # print("*"*120)
    #
    # print("Here is the Summary ")
    # regression_summary = gen_summary(result_folders)
    # pp(regression_summary)
