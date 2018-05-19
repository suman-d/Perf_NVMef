'''This is part of Perf_NVMef Tool Kit
   This tool will generate charts in HTML for different tests \
   This is internally used by the Dashboard.py'''

# Author : Suman Debnath
# E-Mail : suman.debnath@toshiba-tsip.com
# Last Update: 13-March-2018
# Version: 1.1


import os
import pandas as pd
import argparse
import plotly.offline as pyo
import plotly.graph_objs as go


def ParseArgs():
    """Parse command line options into globals."""
    global result_folders

    parser = argparse.ArgumentParser(
                 formatter_class=argparse.RawDescriptionHelpFormatter,
    description="This is a part of KumoScale Performance QA Regression Testing tool. \n"\
                "The module will generate charts from all the given folders \n",
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

def results_df(folders):
    '''Loads the DataFrame for Baseline and Build'''

    runs_dict = {}
    num = 1
    for f in folders:
        f_name = os.path.basename(f)
        _ = f_name.lower().split("_")
        if "baseline" in _:
            result_file = os.path.join(f, "final.csv")
            df = pd.read_csv(result_file)
            runs_dict["baseline"] = [_[3], df]


        else:
            k = "build_" + str(num)
            result_file = os.path.join(f, "final.csv")
            df = pd.read_csv(result_file)
            runs_dict[k] = [_[3], df]
            num +=1


    return runs_dict

def version_check(all_tests):
    '''Checks the build version and isolate baseline with build runs'''

    global all_runs
    versions = []
    for i in all_runs:
        versions.append(all_runs[i][0])

    return min(versions), max(versions)

def bandwidth_blocksize(test_name, chart_title, all_tests):

    _, latest_version = version_check(all_tests)

    data = []
    bs_str = {  512: "512",
                1024: "1K",
                2048: "2K",
                4096: "4K",
                8192: "8K",
                16384: "16K",
                32768: "32K",
                65536: "64K",
                131072: "128K"
             }

    for test in all_tests:
        num = 1
        if test == "baseline":
            df_1 = all_tests[test][1]
            df_1_version = all_tests[test][0] + "(Baseline)"
            baseline_ver = df_1_version

            df_1 = df_1[df_1["Test_Name"] == test_name]
            df_1.index = range(1, len(df_1.index)+1)

            df_baseline_full = df_1.copy()

            df_1 = df_1[["Block Size", "Bandwidth (MB/s)", "Appliance_CPU_Utilization", "Appliance_Memory_Utilization"]]
            df_1["Block Size"] = [ bs_str[i] for i in df_1["Block Size"]]

            # Adding Data
            x_block_size = [str(i) for i in df_1["Block Size"]]

            y1_df1_BW = df_1["Bandwidth (MB/s)"]
            y2_df1_CPU = df_1["Appliance_CPU_Utilization"]
            y3_df1_Mem = df_1["Appliance_Memory_Utilization"]


            trace0=go.Scatter(x=x_block_size,
                                y = y1_df1_BW,
                                name = df_1_version,
                                line = dict(width = 4),
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False)

            trace1 = go.Scatter(x = x_block_size,
                                y = y2_df1_CPU,
                                name = "CPU Utilization " + df_1_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            trace2 = go.Scatter(x = x_block_size,
                                y = y3_df1_Mem,
                                name = "Memory Utilization " + df_1_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            data.append(trace0)
            data.append(trace1)
            data.append(trace2)

            base_df = df_1.copy()

        else:

            df_run = all_tests[test][1]
            df_run_version = all_tests[test][0]

            df_run = df_run[df_run["Test_Name"] == test_name]
            df_run.index = range(1, len(df_run.index)+1)

            df_run_full = df_run.copy()

            df_run = df_run[["Block Size", "Bandwidth (MB/s)", "Appliance_CPU_Utilization", "Appliance_Memory_Utilization"]]
            df_run["Block Size"] = [ bs_str[i] for i in df_run["Block Size"]]

            # Adding Data
            x_block_size = [str(i) for i in df_run["Block Size"]]

            y1_df_run_BW = df_run["Bandwidth (MB/s)"]
            y2_df_run_CPU = df_run["Appliance_CPU_Utilization"]
            y3_df_run_Mem = df_run["Appliance_Memory_Utilization"]


            if df_run_version == latest_version:
                df_run_version += "(Latest)"
                latest_df = df_run.copy()
                latest_ver = df_run_version

            trace0 = go.Scatter(x = x_block_size,
                                y = y1_df_run_BW,
                                name = df_run_version,
                                line = dict(width = 4),
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False)

            trace1 = go.Scatter(x = x_block_size,
                                y = y2_df_run_CPU,
                                name = "CPU Utilization " + df_run_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            trace2 = go.Scatter(x = x_block_size,
                                y = y3_df_run_Mem,
                                name = "Memory Utilization " + df_run_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            data.append(trace0)
            data.append(trace1)
            data.append(trace2)


    layout = go.Layout(title = chart_title,
                       xaxis = dict(title = "Block Size (in Bytes)"),
                       yaxis = dict(title = "Throughput (in MBps)" ),
                       yaxis2=dict(title='Appliance Resource Utilization (in %)',
                        titlefont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        tickfont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        overlaying='y',
                        side='right'),
                        legend=dict(y=1, x=1.05, orientation='v'))


    fig = dict(data=data, layout=layout)

    f_name = "BW_" + chart_title.replace(" ", "_") + ".html"

    data = [pyo.plot(fig, filename=f_name, auto_open=False), base_df, latest_df, df_baseline_full, df_run_full, baseline_ver, latest_ver, fig]

    #return pyo.plot(fig, filename=f_name, auto_open=False), base_df, latest_df
    return data

def iops_qd(test_name, chart_title, all_tests):

    _, latest_version = version_check(all_tests)

    data =[]
    for test in all_tests:
        num = 1
        if test == "baseline":
            df_1 = all_tests[test][1]
            df_1_version = all_tests[test][0] + "(Baseline)"
            baseline_ver = df_1_version


            df_1 = df_1[df_1["Test_Name"] == test_name]
            df_1.index = range(1, len(df_1.index)+1)

            df_baseline_full = df_1.copy()

            df_1 = df_1[["Threads", "IOPS", "Appliance_CPU_Utilization", "Appliance_Memory_Utilization"]]


            # Adding Data
            x_qd = [str(i) for i in df_1["Threads"]]
            y1_df1_IOPS = df_1["IOPS"]
            y2_df1_CPU = df_1["Appliance_CPU_Utilization"]
            y3_df1_Mem = df_1["Appliance_Memory_Utilization"]


            trace0 = go.Scatter(x = x_qd,
                                y = y1_df1_IOPS,
                                name = df_1_version,
                                line = dict(width = 4),
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False)

            trace1 = go.Scatter(x = x_qd,
                                y = y2_df1_CPU,
                                name = "CPU Utilization " + df_1_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            trace2 = go.Scatter(x = x_qd,
                                y = y3_df1_Mem,
                                name = "Memory Utilization " + df_1_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            data.append(trace0)
            data.append(trace1)
            data.append(trace2)

            base_df = df_1.copy()

        else:

            df_run = all_tests[test][1]
            df_run_version = all_tests[test][0]


            df_run = df_run[df_run["Test_Name"] == test_name]
            df_run.index = range(1, len(df_run.index)+1)

            df_run_full = df_run.copy()

            df_run = df_run[["Threads", "IOPS", "Appliance_CPU_Utilization", "Appliance_Memory_Utilization"]]


            # Adding Data
            x_qd = [str(i) for i in df_run["Threads"]]

            y1_df_run_IOPS = df_run["IOPS"]
            y2_df_run_CPU = df_run["Appliance_CPU_Utilization"]
            y3_df_run_Mem = df_run["Appliance_Memory_Utilization"]

            if df_run_version == latest_version:
                df_run_version += "(Latest)"
                latest_df = df_run.copy()
                latest_ver = df_run_version

            trace0 = go.Scatter(x = x_qd,
                                y = y1_df_run_IOPS,
                                name = df_run_version,
                                line = dict(width = 4),
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False)

            trace1 = go.Scatter(x = x_qd,
                                y = y2_df_run_CPU,
                                name = "CPU Utilization " + df_run_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            trace2 = go.Scatter(x = x_qd,
                                y = y3_df_run_Mem,
                                name = "Memory Utilization " + df_run_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            data.append(trace0)
            data.append(trace1)
            data.append(trace2)


    layout = go.Layout(title = chart_title,
                       xaxis = dict(title = "Queue Depth"),
                       yaxis = dict(title = "IOPS" ),
                       yaxis2=dict(title='Appliance Resource Utilization (in %)',
                        titlefont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        tickfont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        overlaying='y',
                        side='right'),
                        legend=dict(y=1, x=1.05, orientation='v'))


    fig = dict(data=data, layout=layout)

    f_name = "IOPS_" + chart_title.replace(" ", "_") + ".html"

    data = [pyo.plot(fig, filename=f_name, auto_open=False), base_df, latest_df, df_baseline_full, df_run_full, baseline_ver, latest_ver, fig]

    #return pyo.plot(fig, filename=f_name, auto_open=False), base_df, latest_df
    return data

def iops_bs(test_name, chart_title, all_tests):

    _, latest_version = version_check(all_tests)

    data = []
    bs_str = {  512: "512",
                1024: "1K",
                2048: "2K",
                4096: "4K",
                8192: "8K",
                16384: "16K",
                32768: "32K",
                65536: "64K",
                131072: "128K"
             }


    for test in all_tests:
        num = 1
        if test == "baseline":
            df_1 = all_tests[test][1]
            df_1_version = all_tests[test][0] + "(Baseline)"
            baseline_ver = df_1_version

            df_1 = df_1[df_1["Test_Name"] == test_name]
            df_1.index = range(1, len(df_1.index)+1)

            df_baseline_full = df_1.copy()

            df_1 = df_1[["Block Size", "IOPS", "Appliance_CPU_Utilization", "Appliance_Memory_Utilization"]]
            df_1["Block Size"] = [ bs_str[i] for i in df_1["Block Size"]]


            # Adding Data
            x_block_size = [str(i) for i in df_1["Block Size"]]
            y1_df1_IOPS = df_1["IOPS"]
            y2_df1_CPU = df_1["Appliance_CPU_Utilization"]
            y3_df1_Mem = df_1["Appliance_Memory_Utilization"]


            trace0 = go.Scatter(x = x_block_size,
                                y = y1_df1_IOPS,
                                name = df_1_version,
                                line = dict(width = 4),
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False)

            trace1 = go.Scatter(x = x_block_size,
                                y = y2_df1_CPU,
                                name = "CPU Utilization " + df_1_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            trace2 = go.Scatter(x = x_block_size,
                                y = y3_df1_Mem,
                                name = "Memory Utilization " + df_1_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            data.append(trace0)
            data.append(trace1)
            data.append(trace2)

            base_df = df_1.copy()

        else:

            df_run = all_tests[test][1]
            df_run_version = all_tests[test][0]


            df_run = df_run[df_run["Test_Name"] == test_name]
            df_run.index = range(1, len(df_run.index)+1)

            df_run_full = df_run.copy()

            df_run = df_run[["Block Size", "IOPS", "Appliance_CPU_Utilization", "Appliance_Memory_Utilization"]]
            df_run["Block Size"] = [ bs_str[i] for i in df_run["Block Size"]]

            # Adding Data
            x_block_size = [str(i) for i in df_run["Block Size"]]

            y1_df_run_IOPS = df_run["IOPS"]
            y2_df_run_CPU = df_run["Appliance_CPU_Utilization"]
            y3_df_run_Mem = df_run["Appliance_Memory_Utilization"]

            if df_run_version == latest_version:
                df_run_version += "(Latest)"
                latest_df = df_run.copy()
                latest_ver = df_run_version

            trace0 = go.Scatter(x = x_block_size,
                                y = y1_df_run_IOPS,
                                name = df_run_version,
                                line = dict(width = 4),
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False)

            trace1 = go.Scatter(x = x_block_size,
                                y = y2_df_run_CPU,
                                name = "CPU Utilization " + df_run_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            trace2 = go.Scatter(x = x_block_size,
                                y = y3_df_run_Mem,
                                name = "Memory Utilization " + df_run_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            data.append(trace0)
            data.append(trace1)
            data.append(trace2)

    layout = go.Layout(title = chart_title,
                       xaxis = dict(title = "Block Size (in Bytes)"),
                       yaxis = dict(title = "IOPS" ),
                       yaxis2=dict(title='Appliance Resource Utilization (in %)',
                        titlefont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        tickfont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        overlaying='y',
                        side='right'),
                        legend=dict(y=1, x=1.05, orientation='v'))


    fig = dict(data=data, layout=layout)

    f_name = "IOPS_" + chart_title.replace(" ", "_") + ".html"

    data = [pyo.plot(fig, filename=f_name, auto_open=False), base_df, latest_df, df_baseline_full, df_run_full, baseline_ver, latest_ver, fig]

    #return pyo.plot(fig, filename=f_name, auto_open=False), base_df, latest_df
    return data

def lat_qd(test_name, chart_title, all_tests):

    _, latest_version = version_check(all_tests)

    data =[]
    for test in all_tests:
        num = 1
        if test == "baseline":
            df_1 = all_tests[test][1]
            df_1_version = all_tests[test][0] + "(Baseline)"
            baseline_ver = df_1_version


            if "write" in test_name.lower():
                col = "Write Latency (us)"
            else:
                col = "Read Latency (us)"

            df_1 = df_1[df_1["Test_Name"] == test_name]
            df_1.index = range(1, len(df_1.index)+1)

            df_baseline_full = df_1.copy()

            df_1 = df_1[["Threads", "Appliance_CPU_Utilization", "Appliance_Memory_Utilization", col]]


            # Adding Data
            x_qd = [str(i) for i in df_1["Threads"]]
            y1_df1_LAT = df_1[col]
            y2_df1_CPU = df_1["Appliance_CPU_Utilization"]
            y3_df1_Mem = df_1["Appliance_Memory_Utilization"]


            trace0 = go.Scatter(x = x_qd,
                                y = y1_df1_LAT,
                                name = df_1_version,
                                line = dict(width = 4),
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False)

            trace1 = go.Scatter(x = x_qd,
                                y = y2_df1_CPU,
                                name = "CPU Utilization " + df_1_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            trace2 = go.Scatter(x = x_qd,
                                y = y3_df1_Mem,
                                name = "Memory Utilization " + df_1_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            data.append(trace0)
            data.append(trace1)
            data.append(trace2)

            base_df = df_1.copy()

        else:

            df_run = all_tests[test][1]
            df_run_version = all_tests[test][0]

            if "write" in test_name.lower():
                col = "Write Latency (us)"
            else:
                col = "Read Latency (us)"

            df_run = df_run[df_run["Test_Name"] == test_name]
            df_run.index = range(1, len(df_run.index)+1)

            df_run_full = df_run.copy()

            df_run = df_run[["Threads", "IOPS", "Appliance_CPU_Utilization", "Appliance_Memory_Utilization", col]]


            # Adding Data
            x_qd = [str(i) for i in df_run["Threads"]]

            y1_df_run_LAT = df_run[col]
            y2_df_run_CPU = df_run["Appliance_CPU_Utilization"]
            y3_df_run_Mem = df_run["Appliance_Memory_Utilization"]

            if df_run_version == latest_version:
                df_run_version += "(Latest)"
                latest_df = df_run.copy()
                latest_ver = df_run_version

            trace0 = go.Scatter(x = x_qd,
                                y = y1_df_run_LAT,
                                name = df_run_version,
                                line = dict(width = 4),
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False)

            trace1 = go.Scatter(x = x_qd,
                                y = y2_df_run_CPU,
                                name = "CPU Utilization " + df_run_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            trace2 = go.Scatter(x = x_qd,
                                y = y3_df_run_Mem,
                                name = "Memory Utilization " + df_run_version,
                                mode='markers',
                                hoverlabel = { "namelength" : -1},
                                cliponaxis = False,
                                yaxis='y2')

            data.append(trace0)
            data.append(trace1)
            data.append(trace2)


    layout = go.Layout(title = chart_title,
                       xaxis = dict(title = "Queue Depth"),
                       yaxis = dict(title = col ),
                       yaxis2=dict(title='Appliance Resource Utilization (in %)',
                        titlefont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        tickfont=dict(
                            color='rgb(148, 103, 189)'
                        ),
                        overlaying='y',
                        side='right'),
                        legend=dict(y=1, x=1.05, orientation='v'))


    fig = dict(data=data, layout=layout)

    f_name = "LAT_" + chart_title.replace(" ", "_") + ".html"

    data = [pyo.plot(fig, filename=f_name, auto_open=False), base_df, latest_df, df_baseline_full, df_run_full, baseline_ver, latest_ver, fig]

    #return pyo.plot(fig, filename=f_name, auto_open=False), base_df, latest_df
    return data

def chart_gen(result_folders):

    global all_runs

    pwd = os.getcwd()
    for f in result_folders:
        result_folders_full_path.append(os.path.join(pwd, f))

    all_runs = results_df(result_folders_full_path)
    #
    # Bandwidth Charts
    ## Chart 1 - Sustained Multi-Threaded Sequential Read Tests by Block Size
    test_name = "Sustained Multi-Threaded Sequential Read Tests by Block Size"
    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version,  fig = bandwidth_blocksize(test_name = test_name,
                                                                                             chart_title="Sustained Multi-Threaded Sequential Read Tests by Block Size",
                                                                                             all_tests=all_runs)

    test_name = test_name + "_BW"

    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]

    ## Chart 2 - Sustained Multi-Threaded Random Read Tests by Block Size(QD=256)
    test_name = "Sustained Multi-Threaded Random Read Tests by Block Size"
    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig = bandwidth_blocksize(test_name = test_name,
                                                                                             chart_title="Sustained Multi-Threaded Random Read Tests by Block Size",
                                                                                             all_tests=all_runs)
    test_name = test_name + "_BW"
    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]

    ## Chart 3 - Sequential Write Tests with Queue Depth=1 by Block Size
    test_name = "Sequential Write Tests with Queue Depth=1 by Block Size"
    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig = bandwidth_blocksize(test_name = test_name,
                                                                                             chart_title="Sequential Write Tests with Queue Depth 1 by Block Size",
                                                                                             all_tests=all_runs)

    test_name = test_name + "_BW"
    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]

    # IOPS charts
    ## Chart 4 - Sustained Multi-Threaded Random Read Tests by Block Size
    test_name = "Sustained Multi-Threaded Random Read Tests by Block Size"
    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig = iops_bs(test_name = test_name,
                                                                                 chart_title="Sustained Multi-Threaded Random Read Tests by Block Size",
                                                                                 all_tests=all_runs)
    test_name = test_name + "_IOPS"
    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]

    ## Chart 5 - Sustained 4KB Random mixed 50% Write Tests by Threads
    test_name = "Sustained 4KB Random mixed 50% Write Tests by Threads"
    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig = iops_qd(test_name = test_name,
                                                                                 chart_title="Sustained Random 4K Mixed Read 50 percent",
                                                                                 all_tests=all_runs)
    test_name = test_name + "_IOPS"
    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]

    ## Chart 6 - Sustained 4K Random Read
    test_name = "Sustained 4KB Random Read Tests by Number of Threads"
    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig = iops_qd(test_name = test_name,
                                                                                 chart_title="Sustained 4K Random Read",
                                                                                 all_tests=all_runs)
    test_name = test_name + "_IOPS"
    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]

    ## Chart 7 - Sustained 4K Random Write
    test_name = "Sustained 4KB Random Write Tests by Number of Threads"
    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig = iops_qd(test_name = test_name,
                                                                                 chart_title="Sustained 4K Random Write",
                                                                                 all_tests=all_runs)
    test_name = test_name + "_IOPS"
    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]

    ## Chart 8 - Latency Test Sustained 4KB Random Read Tests
    test_name = "Latency Test Sustained 4KB Random Read Tests by Number of Threads"
    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig = lat_qd(test_name = test_name,
                                                                                chart_title="Latency Test Sustained 4KB Random Read Tests by Number of Threads",
                                                                                all_tests=all_runs)

    test_name = test_name + "_LAT"
    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]

    ## Chart 9 - Latency Test Sustained 4KB Random Read Tests
    test_name = "Latency Test Sustained 4KB Random Write Tests by Number of Threads"

    chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig = lat_qd(test_name = test_name,
                                                                                chart_title="Latency Test Sustained 4KB Random Write Tests by Number of Threads",
                                                                                all_tests=all_runs)
    test_name = test_name + "_LAT"
    results[test_name] = [chart_path, base_df, latest_df, df_baseline_full, df_run_full, baseline_version, latest_version, fig]


    return results

# For Charts
results = {}
result_folders = ""
result_folders_full_path = []
all_runs = ""

if __name__ == "__main__":

    ParseArgs()
    print("*"*120)
    print("Analyzing the data")

    all_data = chart_gen(result_folders)

    print("*"*120)
    print("Here are all the Tests and its Location : \n")

    for data in all_data:
        print("- "*60)
        print("Test Name : {}".format(data))
        print("Chart Path : {}".format(all_data[data][0]))
        print("Baseline Version : {}".format(all_data[data][-3]))
        print("Current Version : {}".format(all_data[data][-2]))
