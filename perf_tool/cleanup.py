#!/usr/bin/env python3

import yaml
import os
import sys
import random
import socket
import time
import pytest
import json
from lib import toshibaeraptor
from lib import nvmecli_cmds
from pprint import pprint as pp


# Reading the Appliance related info(IP, Storage Configuration, etc.)
with open("config/config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

cert = os.path.abspath('ssdtoolbox.pem')
init_mgmt_ips = [cfg['appliance']['ip']]
no_ssds = cfg['storage_config']['no_ssds_per_group']
no_ssd_groups = cfg['storage_config']['no_ssd_group']
no_targets = cfg['storage_config']['no_targets']
ns_block_size = cfg['storage_config']['namespace_blocksize']
chunk_size = cfg['storage_config']['ssd_group_chunk_size']



# Connecting to the Appliance
eraptor = toshibaeraptor.ToshibaERaptor(init_mgmt_ips, cert)

# Clean the setup, remove any targets and ssd_groups
print("*************************************************************************************************")
print("Clearning the exisiting configuration in the Appliance")
eraptor.cleanup()
print("Cleanup is done")
