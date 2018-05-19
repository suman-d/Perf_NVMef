import urllib3
import json
import abc
import ssl
import os
import logging
urllib3.disable_warnings()
LOG = logging.getLogger(__name__)


class JsonClass:

    def __init__(self):
        pass

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class Target(JsonClass):
    """
    Target data
    """

    def __init__(self, target_id, name, alias, capacity, target_type,parent_alias):
        JsonClass.__init__(self)
        self.targetID = target_id
        self.name = name
        self.alias = alias
        self.capacity = capacity
        self.targetType = target_type
        self.namespaces = []
        self.parentAlias = parent_alias

    def add_namespace(self, namespace):
        self.namespaces.append(namespace)

    @staticmethod
    def create(target_data):
        target_type = target_data['type']
        if target_type == 'SSD_GROUP_TARGET':
            ssd_group=None
            #if target_data.has_key('ssdGroup'):                  # Refactored for Python3
            if 'ssdGroup' in target_data:
                ssd_group = target_data['ssdGroup']
            return SSDGroupTarget(target_data['id'], target_data['name'], target_data['alias'], target_data['capacity'], target_data['targetType'],target_data['parentAlias'],ssd_group)
        elif target_type == 'SSD_TARGET':
            return SSDTarget(target_data['id'], target_data['name'], target_data['alias'], target_data['capacity'], target_data['targetType'],target_data['parentAlias'], target_data['ssd'])
        elif target_type == 'SCM_TARGET':
            return SCMTarget(target_data['id'], target_data['name'], target_data['alias'], target_data['capacity'], target_data['targetType'],target_data['parentAlias'], target_data['scmPartition'])
        return None

    def __str__(self):
        return "(" + str(self.name) + ", " + str(self.alias) + ", " + str(self.capacity) + ", " + str(self.targetType) + ")"


class SSDGroupTarget(Target):
    """
    SSDGroupTarget data
    """

    def __init__(self, target_id, name, alias, capacity, target_type,parent_alias, ssd_group):
        Target.__init__(self, target_id, name, alias, capacity, target_type,parent_alias)
        self.ssdGroup = ssd_group


class SSDTarget(Target):
    """
    SSDTarget data
    """
    def __init__(self, target_id, name, alias, capacity, target_type,parent_alias, ssd):
        Target.__init__(self, target_id, name, alias, capacity, target_type,parent_alias)
        self.ssd = ssd


class SCMTarget(Target):
    """
    SSDGroupTarget data
    """
    def __init__(self, target_id, name, alias, capacity, target_type, parent_alias ,scm_part):
        Target.__init__(self, target_id, name, alias, capacity, target_type,parent_alias)
        self.scmPartition = scm_part


class ACL(JsonClass):
    """
    ACL data
    """

    def __init__(self, permission, discovery_flag, target):
        JsonClass.__init__(self)
        self.permission = permission
        self.discoveryFlag = discovery_flag
        self.target = target


class Initiator(JsonClass):
    """
    Initiator data
    """

    def __init__(self, name, alias_):
        JsonClass.__init__(self)
        self.name = name
        self.alias_ = alias_
        self.aclPolicies = []

    def add_acl(self, acl):
        self.aclPolicies.append(acl)

    def remove_acl_by_target(self, target_alias):
        num_of_acls = len(self.aclPolicies)
        if num_of_acls > 0:
            for acl in self.aclPolicies:
                target = acl.target
                alias = target.alias
                if alias == target_alias:
                    self.aclPolicies.remove(acl)


class SSDGroup(JsonClass):
    """
    SSDGroup data
    """

    def __init__(self, group_id, name, device_type, capacity, free_space):
        JsonClass.__init__(self)
        self.groupID = group_id
        self.name = name
        self.deviceType = device_type
        self.capacity = capacity
        self.free_space = free_space
        self.targets = []

    def add_target(self, target):
        self.targets.append(target)

    def get_all_targets_size(self):
        total_capacity = 0
        num_of_targets = len(self.targets)
        if num_of_targets > 0:
            for target in self.targets:
                total_capacity += target.capacity

        return total_capacity

    def get_target(self, target_alias):
        for t in self.targets:
            if t.alias == target_alias:
                return t
        return None

    def __str__(self):
        return "(" + str(self.name) + ", " + str(self.capacity) + ", " + str(self.targets) + ")"


class Namespace(JsonClass):
    """
    Namespace data
    """

    def __init__(self, name, size, blockSize=512):
        JsonClass.__init__(self)
        self.name = name
        self.size = size
        self.blockSize = blockSize


class Portal(JsonClass):
    """
    Portal data
    """
    def __init__(self, name, ip, port, type, netinterface):
        JsonClass.__init__(self)
        self.name = name
        self.ip = ip
        self.port = port
        self.type = type
        self.netinterface = netinterface

    def __str__(self):
        return "(" + str(self.name) + ", " + str(self.ip) + ", " + str(self.port) + ")"


class TargetGroupAdvice(JsonClass):
    """
    TargetGroupAdvice data
    """

    def __init__(self, requested_target_size):
        JsonClass.__init__(self)
        self.requestedTargetSize = requested_target_size


class Controller(JsonClass):
    """
    Controller data
    """

    def __init__(self, mgmt_ips):
        JsonClass.__init__(self)
        self.mgmt_ips = mgmt_ips


class HostInfo(JsonClass):
    """
    ERaptor data
    """

    def __init__(self, controllers):
        JsonClass.__init__(self)
        self.controllers = controllers

    def get_mgmt_ips(self):
        mgmt_ips = []
        num_of_controllers = len(self.controllers)
        if num_of_controllers > 0:
            for i in range(num_of_controllers):
                curr_controller = self.controllers[i]
                curr_controller_mgmt_ips = curr_controller.mgmt_ips
                num_of_ips = len(curr_controller_mgmt_ips)
                if num_of_ips > 0:
                    mgmt_ips.extend(curr_controller_mgmt_ips)

        return mgmt_ips


class ERaptorVisitor:
    """
    ERaptor Visitor
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, http, command_str):
        self.http = http
        self.command_str = command_str

    @abc.abstractmethod
    def visit(self, url):
        return


class ERaptorGetVisitor(ERaptorVisitor):
    """
    ERaptor Get Visitor
    """

    def visit(self, url):
        r = self.http.request('GET', url)
        return r


class ERaptorPostVisitor(ERaptorVisitor):
    """
    ERaptor Post Visitor
    """

    def __init__(self, http, command_str, json_body):

        ERaptorVisitor.__init__(self, http, command_str)
        self.json_body = json_body

    def visit(self, url):
        r = self.http.request('POST', url, body=self.json_body)
        return r


class ERaptorConnector:
    """
    ERaptor Connector
    """

    def __init__(self, ips, visitor):
        self.visitor = visitor
        self.ips = ips

    def visit_eraptors(self):
        if self.ips:
            num_of_ips = len(self.ips)
            if num_of_ips > 0:
                e = None
                for i in range(num_of_ips):
                    ip = self.ips[i]
                    url = 'https://'+ip+':10121/SSDAgentServer/NVMEOF/v1/'+self.visitor.command_str
                    try:
                        r = self.visitor.visit(url)
                        if r:
                            if i != 0:
                                ToshibaERaptor.switch_path(i)
                            return r
                    except Exception as e:
                        LOG.debug('Exception %s', e.message)
                        continue
                raise e
            raise ValueError("num_of_ips = 0!")
        raise ValueError("self.ips is Null!")


class ToshibaERaptor:
    """
    REST client class that interacts with a specific ERaptor
    """
    mgmt_ips = []

    def __init__(self, ips, cert):
        self.mgmt_ips = ips
        if cert is None:
            cert='ssdtoolbox.pem'
            here = os.path.dirname(__file__)
            cert = os.path.join(here,cert)
        LOG.debug('PEM file %s', cert)
        ToshibaERaptor.mgmt_ips = ips
        self.http = urllib3.PoolManager(cert_reqs=ssl.CERT_NONE, cert_file=cert, assert_hostname=False, timeout=urllib3.Timeout(connect=5.0, read=60.0))
        host_info = self.get_host_info()
        retrieved_ips = host_info.get_mgmt_ips()
        for ip in retrieved_ips:
            if not ip in ToshibaERaptor.mgmt_ips:
                ToshibaERaptor.mgmt_ips.append(ip)

    # Call to switch last successful connected ip
    @staticmethod
    def switch_path(ip_idx):
        temp = ToshibaERaptor.mgmt_ips[0]
        ToshibaERaptor.mgmt_ips[0] = ToshibaERaptor.mgmt_ips[ip_idx]
        ToshibaERaptor.mgmt_ips[ip_idx] = temp

    # Call to ADD_TARGET API
    def create_target(self, target):
        j = target.to_json()
        return self.post_command("executeCommand/ADD_TARGET", j)

    # Call to create SSD Group with only no. of ssds and chunk_size
    def create_ssd_group(self, name, ssds, chunk_size="null"):
        if len(ssds) == 1:
            chunk_size = "null"

        j = {'name': name,
             'chunkSize' : chunk_size,
             'ssds': [{"name" : i} for i in ssds]}
        return self.post_command("executeCommand/ADD_SSD_GROUP", str(j))


    # Call to REMOVE_TARGET API
    def delete_target(self, target):
        j = target.to_json()
        return self.post_command("executeCommand/REMOVE_TARGET", j)

    # Call to REMOVE_TARGET using Alias
    def delete_target_by_alias(self, target):
        j = {'alias':target}
        return self.post_command("executeCommand/REMOVE_TARGET", str(j))

    # Call to REMOVE_SSD_GROUP using ssd_group name
    def delete_ssd_group_by_name(self, ssd_group_name):
        j = {'name':ssd_group_name}
        return self.post_command("executeCommand/REMOVE_SSD_GROUP", str(j))


    # Call to CONNECT_HOST API
    def connect_host(self, initiator):
        j = initiator.to_json()
        return self.post_command("executeCommand/CONNECT_HOST", j)

    # Call to MODIFY_HOST API
    def disconnect_host(self, target, initiator):
        host_name = initiator.name
        target_alias = target.alias
        db_initiator = self.get_initiator(host_name)
        if db_initiator:
            db_initiator.remove_acl_by_target(target_alias)
            j = db_initiator.to_json()
            return self.post_command("executeCommand/MODIFY_HOST", j)
        else:
            result = []
            result['status'] = 'DeviceNotFound'
            result['description'] = "Could not find the initiator: "+ host_name
            return result

    # Call to MODIFY_HOST API
    def modify_host(self, initiator):
        j = initiator.to_json()
        return self.post_command("executeCommand/MODIFY_HOST", j)

    # Operate POST REST request
    def post_command(self, command, json_body):
        r = self.eraptor_post_request(command, json_body)
        if r:
            result = json.loads(r.data)
            return result

    # Call to get only SSDs by ssd_name as list
    def get_ssds_names(self):
        s = self.eraptor_get_request("ssds")
        ssds = []
        ssds_dict = {}
        if s.data:
            s = json.loads(s.data)
            for i in s:
                ssds.append(str(i['name']))
                ssds_dict[str(i['name'])] = i['paths'][0]['name']

        return ssds_dict

    # Call to get ssd_groups API
    def get_ssd_groups(self):
        ssd_groups = []
        r = self.eraptor_get_request("ssd_groups")
        if r:
            if r.data:
                groups_data = json.loads(r.data)
                num_of_ssd_groups = len(groups_data)
                if num_of_ssd_groups > 0:
                    for i in range(num_of_ssd_groups):
                        ssd_group = SSDGroup(groups_data[i]['id'], groups_data[i]['name'], groups_data[i]['type'], groups_data[i]['capacity'], groups_data[i]['freeSpace'])
                        targets_data = groups_data[i]['targets']
                        num_of_targets = len(targets_data)
                        if num_of_targets > 0:
                            for j in range(num_of_targets):
                                target = Target.create(targets_data[j])
                                if target is not None:
                                    target.ssdGroup = ssd_group
                                    ssd_group.add_target(target)
                        ssd_groups.append(ssd_group)
        return ssd_groups

    # Call to get only ssd_groups by name as list
    def get_ssd_group_names(self):
        ssd_groups = [str(i.name) for i in self.get_ssd_groups()]
        return ssd_groups

    # Call to get the list of targets as list
    def get_targets1(self):
        t = self.eraptor_get_request("targets")
        targets = []
        if t.data:
            t = json.loads(t.data)
            for i in t:
                targets.append(str(i['alias']))

        return targets

    # Call to get targets API
    def get_targets(self):
        targets = []
        cmd = "targets"
        r = self.eraptor_get_request(cmd)
        if r:
            if r.data:
                targets_data = json.loads(r.data)
                num_of_targets = len(targets_data)
                if num_of_targets > 0:
                    for i in range(num_of_targets):
                        target = Target.create(targets_data[i])
                        targets.append(target)
        return targets

    # Get target by alias
    def get_target(self, alias):
        targets = self.get_targets()
        num_of_targets = len(targets)
        if num_of_targets > 0:
            for i in range(num_of_targets):
                if alias == targets[i].alias:
                    return targets[i]
        return None

    # Get target by parent alias
    def get_target_by_parent_alias(self, parent_alias):
        targets = self.get_targets()
        num_of_targets = len(targets)
        if num_of_targets > 0:
            for i in range(num_of_targets):
                if parent_alias == targets[i].parentAlias:
                    return targets[i]
        return None

    # Call to get allowed_hosts API
    def get_allowed_hosts(self):
        allowed_hosts = []
        r = self.eraptor_get_request("allowed_hosts")
        if r:
            if r.data:
                hosts_data = json.loads(r.data)
                num_of_hosts = len(hosts_data)
                if num_of_hosts > 0:
                    for i in range(num_of_hosts):
                        initiator = Initiator(hosts_data[i]['name'], hosts_data[i]['alias_'])
                        acls_data = hosts_data[i]['aclPolicies']
                        num_of_acls = len(acls_data)
                        if num_of_acls > 0:
                            for j in range(num_of_acls):
                                target_data = acls_data[j]['target']
                                target = Target.create(target_data)
                                acl = ACL(acls_data[j]['permission'], acls_data[j]['discoverFlag'], target)
                                initiator.add_acl(acl)
                        allowed_hosts.append(initiator)
        return allowed_hosts

    # Get initiator by host name
    def get_initiator(self, host_name):
        hosts = self.get_allowed_hosts()
        num_of_hosts = len(hosts)
        if num_of_hosts > 0:
            for i in range(num_of_hosts):
                if host_name == hosts[i].name:
                    return hosts[i]
        return None

    # Get ssd group by group name
    def get_ssd_group(self, group_name):
        groups = self.get_ssd_groups()
        num_of_groups = len(groups)
        if num_of_groups > 0:
            for i in range(num_of_groups):
                if group_name == groups[i].name:
                    return groups[i]
        return None

    # Call to get ssd_groups API
    def get_portals(self, portal_type):
        portals = []
        r = self.eraptor_get_request("portals")
        if r:
            if r.data:
                portals_data = json.loads(r.data)
                num_portals = len(portals_data)
                if num_portals > 0:
                    for i in range(num_portals):
                        portal = Portal(portals_data[i]['name'], portals_data[i]['ip']['name'], portals_data[i]['port'],portals_data[i]['portalType'], portals_data[i]['ip']['netInterface']['name'])
                        if portal_type is None or portal_type == portal.type:
                            portals.append(portal)
        return portals

    # Call to get portal name, portal IP and portal interface
    def get_portals_all(self):
        portals = self.get_portals("NVME")
        portals_list = []
        for p in portals:
            portal_info = {}
            portal_info["name"], portal_info["netinterface"], portal_info["ip"] = (p.name, p.netinterface, p.ip)
            portals_list.append(portal_info)

        return portals_list

    # Call to get host_info API
    def get_host_info(self):
        host_info = None
        controllers = []
        r = self.eraptor_get_request("info")
        if r:
            if r.data:
                host_info_data = json.loads(r.data)
                controllers_data = host_info_data['controllers']
                num_controllers = len(controllers_data)
                if num_controllers > 0:
                    for i in range(num_controllers):
                        controllers_mgmt_ips = []
                        nics_data = controllers_data[i]['nics']
                        num_nics = len(nics_data)
                        if num_nics > 0:
                            for j in range(num_nics):
                                interfaces_data = nics_data[j]['interfaces']
                                num_interfaces = len(interfaces_data)
                                if num_interfaces > 0:
                                    for k in range(num_interfaces):
                                        interface_type = interfaces_data[k]['interfaceType']
                                        if interface_type == "MGMT":
                                            ip_addresses_data = interfaces_data[k]['ipAddresses']
                                            num_ip_addresses = len(ip_addresses_data)
                                            if num_ip_addresses > 0:
                                                for s in range(num_ip_addresses):
                                                    ip_address = ip_addresses_data[s]['name']
                                                    controllers_mgmt_ips.append(ip_address)
                        curr_controller = Controller(controllers_mgmt_ips)
                        controllers.append(curr_controller)
                host_info = HostInfo(controllers)

        return host_info

    # Call to get host Utilization
    def get_host_utilization(self):
        r = self.eraptor_get_request("host_utilization")
        host_util = json.loads(r.data)
        return host_util

    # Call to clean up the ERaptor
    def cleanup(self):
        ''' It will delete all the targets and SSD Groups(if any)
        from the appliance, it will not touch portals, it will delete all the
        abstract targets, transparent targets and ssd groups'''

        # Get targets alias in a list
        t_ali_targets = []
        targets = self.get_targets()
        num_of_targets = len(targets)
        if num_of_targets > 0:
            for target in targets:
                t_ali_targets.append(str(target.alias))

        # Delete targets
        for i in t_ali_targets:
            self.delete_target_by_alias(i)

        # Get SSD groups
        ssd_groups = self.get_ssd_group_names()

        # Delete groups (if any)
        for i in ssd_groups:
            self.delete_ssd_group_by_name(i)


    # Call to TARGET_GROUP_ADVICE API
    def auto_group_advice(self, target_group_advice):
        j = target_group_advice.to_json()
        return self.post_command("executeCommand/TARGET_GROUP_ADVICE", j)

    # Call ERaptor with get request
    def eraptor_get_request(self, api_name):
        get_visitor = ERaptorGetVisitor(self.http, api_name)
        eraptor_connector = ERaptorConnector(ToshibaERaptor.mgmt_ips, get_visitor)
        r = eraptor_connector.visit_eraptors()

        return r

    # Call ERaptor with post request
    def eraptor_post_request(self, api_name, json_body):
        get_visitor = ERaptorPostVisitor(self.http, api_name, json_body)
        eraptor_connector = ERaptorConnector(ToshibaERaptor.mgmt_ips, get_visitor)
        r = eraptor_connector.visit_eraptors()

        return r
