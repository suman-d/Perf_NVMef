
'''This is part of Perf_NVMef Tool Kit
   This tool will generate charts and start a local webserver with performance dashboard
   This will also same all the seperate charts in HTML'''

# Author : Suman Debnath
# E-Mail : suman.debnath@toshiba-tsip.com
# Last Update: 13-March-2018
# Version: 1.1


import argparse
import json
import os
import dash
import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
from collections import OrderedDict
from pprint import pprint as pp


import Chart_Gen
import Regression_Cal


def ParseArgs():
    """Parse command line options into globals."""
    global result_folders

    parser = argparse.ArgumentParser(
                 formatter_class=argparse.RawDescriptionHelpFormatter,
    description="This is a part of KumoScale Performance QA Regression Testing tool. \n" \
                "The module will generate charts from all the given folders \n",
    epilog="""
    Requirements:\n
    * Already completed a test run using "nvmef_perf" tool and the "Result" folder is available
    * Already completed running "post_test_data_collector" tool for all the result folders
    * All the result folder are located in the present working directory, which this script is present
    \n\n
    """)
    # parser.add_argument("--resultFolders", "-f", dest = "result_folders",
    #     help="Provide Test Result Folder Seperated by space", required=True)
    parser.add_argument("--resultFolders", "-f", dest = "result_folders",
        help="Provide Test Result Folder Seperated by space", required=False,
        default=" ".join(result_folders))

    args = parser.parse_args()

    result_folders = args.result_folders.split()


# print button

def print_button():
    printButton = html.A(['Print PDF'],className="button no-print print",style={'position': "absolute", 'top': '-40', 'right': '0'})
    return printButton

# reusable componenets
def make_dash_table(df):
    ''' Return a dash definitio of an HTML table for a Pandas dataframe '''
    table = []
    for index, row in df.iterrows():
        html_row = []
        for i in range(len(row)):
            html_row.append(html.Td([row[i]]))
        table.append(html.Tr(html_row))
    return table


# includes page/full view
def get_logo():

    img_path = os.path.join(os.getcwd(), "ks.png")
    logo = html.Div([
            html.Img(src='http://logonoid.com/images/toshiba-logo.jpg', height='40', width='160')
        ], className="ten columns padded")
    return logo

def get_header():
    header = html.Div([

        html.Div([
            html.H1(
                'Toshiba KumoScale QA Performance Regression Dashboard')
        ], className="twelve columns padded",
           style={'text-align': 'center', 'margin-bottom': '15px', 'color': '#DC143C'})
        ], className="row gs-header gs-text-header")
    return header

def exe_summary_df(exe_summary):

    all_df = []

    for data in exe_summary:
        if data == "Bandwidth" and len(exe_summary[data]) != 0:
            df_bw = pd.DataFrame(data=exe_summary['Bandwidth'], columns=["Bandwidth"])
            df_bw.index = range(1, len(df_bw.index)+1)

            all_df.append(df_bw)

        elif data == "Latency" and len(exe_summary[data]) != 0:
            df_lat = pd.DataFrame(data=exe_summary['Latency'], columns=["Latency"])
            df_lat.index = range(1, len(df_lat.index)+1)

            all_df.append(df_lat)

        elif data == "IOPS" and len(exe_summary[data]) != 0:
            df_iops = pd.DataFrame(data=exe_summary['IOPS'], columns=["IOPS"])
            df_iops.index = range(1, len(df_iops.index)+1)

            all_df.append(df_iops)


    present_time = exe_summary["Date"]
    latest_version = exe_summary["Latest Version"].split("(")[0]
    baseline_version = exe_summary["Baseline Version"].split("(")[0]

    return all_df, latest_version, baseline_version, present_time


def perf_dash(all_data, regression_summary):
    global app

    all_df, latest_version, baseline_version, present_time = exe_summary_df(exe_summary=regression_summary)
    app = dash.Dash()
    graph_fig = { data: all_data[data][-1] for data in all_data }
    app.layout = html.Div([         get_logo(),
                                    get_header(),

                                    html.Div([html.H2('Executive Summary',
                                                     className="gs-header gs-text-header padded"),
                                                    html.P("This Report is generated on {}".format(present_time)),
                                                    html.P("The Latest Version of KumoScale in this report is {}".format(latest_version)),
                                                    html.P("The Baseline Version of KumoScale in this report is {}".format(baseline_version))]
                                                    , className="six columns"),
                                    html.Div([html.H2('Test Configuration',
                                                     className="gs-header gs-text-header padded"),
                                                    html.P("Target Configuration 1 SSD > 1 Group > 1 Abstract Target"),
                                                    html.P("Total Nos. of SSD used in this test is 12"),
                                                    html.P("Total Nos. of hosts used in this test is 2")]
                                                    , className="six columns"),

                                    html.Div([ html.H2(["Regression Summary For Bandwidth Tests"],
                                                       className="gs-header gs-table-header padded"),
                                                       html.Table(make_dash_table(all_df[0]))
                                             ], className="six columns"),
                                    html.Div([ html.H2(["Regression Summary For Latency Tests"],
                                                       className="gs-header gs-table-header padded"),
                                                       html.Table(make_dash_table(all_df[1]))
                                             ], className="six columns"),
                                    html.Div([ html.H2(["Regression Summary For IOPS Tests"],
                                                       className="gs-header gs-table-header padded"),
                                                       html.Table(make_dash_table(all_df[2]))
                                             ], className="six columns"),

                                    html.Div([ html.H1(["Performance Test Charts"],
                                                       className="gs-header gs-table-header padded")
                                              ],
                                              style={'text-align': 'center', 'margin-bottom': '15px', 'color': '#32CD32'},
                                              className="six columns"),
                                    html.Div([ dcc.Graph(id=data, figure=graph_fig[data])   for data in graph_fig])
                        ])



    # Update page
    # @app.callback(dash.dependencies.Output('page-content', 'children'),
    #               [dash.dependencies.Input('url', 'pathname')])
    # def display_page(pathname):
    #     if pathname == '/' or pathname == '/overview':
    #         return overview
    #
    # external_css = ["https://cdnjs.cloudflare.com/ajax/libs/normalize/7.0.0/normalize.min.css",
    #                 "https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
    #                 "//fonts.googleapis.com/css?family=Raleway:400,300,600",
    #                 "https://codepen.io/bcd/pen/KQrXdb.css",
    #                 "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css"]
    #
    # for css in external_css:
    #     app.css.append_css({"external_url": css})
    #
    # external_js = ["https://code.jquery.com/jquery-3.2.1.min.js",
    #                "https://codepen.io/bcd/pen/YaXojL.js"]

    # for js in external_js:
    #     app.scripts.append_script({"external_url": js})



# Starts Here,
# Global Variables
#result_folders = ""
pwd= os.getcwd()
result_folders = [ os.path.join(pwd, f) for f in os.listdir(os.getcwd()) if os.path.isdir(f) and f.lower().startswith("result")]

app = ""

if __name__ == '__main__':

    ParseArgs()
    all_data = Chart_Gen.chart_gen(result_folders)
    regression_summary = Regression_Cal.gen_summary(all_data)

    # Writing Executive Summary in the form of JSON in a file called "Executive_Summary.json"
    json_string = json.dumps(regression_summary)
    filename = "Executive_Summary.json"
    with open(filename, 'w') as f:
        json.dump(regression_summary, f)

    # Create the Dashboard webserver
    perf_dash(all_data, regression_summary)

    # Start the Dashboard webserver
    app.run_server(host='0.0.0.0', debug=True)
