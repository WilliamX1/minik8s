import random
import time

from flask import Flask, request
import json
import uuid
import etcd3
import sys
import os
import requests
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, os.path.pardir)
sys.path.append(os.path.join(BASE_DIR, '../helper'))
import utils, const, yaml_loader
from serverless import ServerlessFunction, Edge, DAG

sys.path.append(os.path.join(BASE_DIR, '../worker'))
from entities import parse_bytes
import etcd_controller

app = Flask(__name__)
# CORS(app, supports_credentials=True)

use_etcd = False  # True
etcd = etcd3.client(port=2379)
etcd_supplant = dict()
api_server_url = None


def get(key, assert_exist=True):
    if use_etcd:
        value, _ = etcd.get(key)
        if value:
            return json.loads(value)
    else:
        if etcd_supplant.__contains__(key):
            return json.loads(etcd_supplant[key])  # force deep copy here
    # key not exist
    if assert_exist:
        raise FileNotFoundError
    return None


def put(key, value):
    if use_etcd:
        etcd.put(key, json.dumps(value))
    else:
        etcd_supplant[key] = json.dumps(value)  # force deep copy here


def get_api_server_url():
    return get('api_server_url')


def init_api_server():
    global api_server_url
    # start etcd
    f = open(const.MASTER_API_SERVER_URL_PATH, 'r')
    API_SERVER_URL = str(f.read())
    print(API_SERVER_URL)
    f.close()
    # for the very first start, init etcd
    put('api_server_url', API_SERVER_URL)
    api_server_url = get('api_server_url')
    if get('nodes_list', assert_exist=False) is None:
        put('nodes_list', list())
    if get('pods_list', assert_exist=False) is None:
        put('pods_list', list())
    if get('services_list', assert_exist=False) is None:
        put('services_list', list())
    if get('replica_sets_list', assert_exist=False) is None:
        put('replica_sets_list', list())
    if get('dag_list', assert_exist=False) is None:
        put('dag_list', list())
    if get('functions_list', assert_exist=False) is None:
        put('functions_list', list())
    if get('hpa_list', assert_exist=False) is None:
        put('hpa_list', list())
    if get('jobs_list', assert_exist=False) is None:
        put('jobs_list', list())
    if get('dns_list', assert_exist=False) is None:
        put('dns_list', list())
    if get('dns_config', assert_exist=False) is None:
        put('dns_config', dict())


def delete_key(key):
    if use_etcd:
        etcd.delete(key)
    else:
        etcd_supplant.pop(key)


@app.route('/Node', methods=['GET'])
def handle_nodes():
    result = dict()
    result['nodes_list']: list = get('nodes_list')
    for node_instance_name in result['nodes_list']:
        result[node_instance_name] = get(node_instance_name)
        try:  # we allow timeout
            r = requests.get(url=result[node_instance_name]['url'] + "/heartbeat", timeout=0.01)
        except Exception as e:
            pass
    return json.dumps(result)


@app.route('/Node', methods=['POST'])
def upload_nodes():
    json_data = request.json
    node_config: dict = json.loads(json_data)
    node_instance_name = node_config['instance_name']
    node_config['last_receive_time'] = time.time()
    node_config['status'] = 'READY TO START'

    # print("node_config = ", node_config)
    nodes_list: list = get('nodes_list')
    # node instance name bind with physical mac address
    flag = 0
    for name in nodes_list:
        if name == node_instance_name:
            flag = 1
    if not flag:
        nodes_list.append(node_instance_name)
    put('nodes_list', nodes_list)
    put(node_instance_name, node_config)
    return json.dumps(get('nodes_list')), 200


@app.route('/Node/<string:node_instance_name>', methods=['DELETE'])
def delete_node(node_instance_name: str):
    # set node to not available
    node_instance_config = get(node_instance_name)
    node_instance_config['status'] = 'Not Available'
    put(node_instance_name, node_instance_config)  # save changed status
    # set pod to lost connect
    pods_list = get('pods_list')
    for pod_instance_name in pods_list:
        pod_config = get(pod_instance_name)
        if pod_config.__contains__('node') and pod_config['node'] == node_instance_name:
            pod_config['status'] = 'Lost Connect'
            put(pod_instance_name, pod_config)  # save changed status
    return json.dumps(get('nodes_list')), 200


@app.route('/Node/<string:node_instance_name>', methods=['GET'])
def get_node_instance(node_instance_name: str):
    # set node to not available
    node_instance_config = get(node_instance_name, assert_exist=False)
    if node_instance_config:
        if node_instance_config.get('pod_instances'):
            for pod_instance_name in node_instance_config['pod_instances']:
                node_instance_config[pod_instance_name] = get(pod_instance_name)
        return json.dumps(node_instance_config), 200
    else:
        return json.dumps(dict()), 200


@app.route('/', methods=['GET'])
def get_all():
    return json.dumps('not good'), 200


@app.route('/Pod', methods=['GET'])
def get_pods():
    result = dict()
    result['pods_list'] = get('pods_list')
    for pod_instance_name in result['pods_list']:
        pod_config = get(pod_instance_name, assert_exist=False)
        if pod_config:
            result[pod_instance_name] = pod_config
    return json.dumps(result), 200


@app.route('/Service', methods=['GET'])
def get_services():
    result = dict()
    result['services_list'] = get('services_list')
    for service_instance_name in result['services_list']:
        service_config = get(service_instance_name, assert_exist=False)
        # print("Service = ", service_instance_name)
        if service_config:
            result[service_instance_name] = service_config
    return json.dumps(result), 200


@app.route('/ReplicaSet', methods=['GET'])
def get_replica_set():
    result = dict()
    result['replica_sets_list'] = get('replica_sets_list')
    for replica_set_instance in result['replica_sets_list']:
        config = get(replica_set_instance)
        result[replica_set_instance] = config
        for pod_instance_name in config['pod_instances']:
            pod_config = get(pod_instance_name, assert_exist=False)
            if pod_config:
                result[pod_instance_name] = pod_config
    # print(result)
    return json.dumps(result), 200


@app.route('/HorizontalPodAutoscaler', methods=['GET'])
def get_hpa():
    result = dict()
    result['hpa_list'] = get('hpa_list')
    for hpa_instance in result['hpa_list']:
        config = get(hpa_instance)
        result[hpa_instance] = config
    return json.dumps(result), 200


@app.route('/HorizontalPodAutoscaler', methods=['POST'])
def upload_hpa():
    json_data = request.json
    HPA_config: dict = json.loads(json_data)
    assert HPA_config['kind'] == 'HorizontalPodAutoscaler'
    replica_set_instance_name = HPA_config['name'] + uuid.uuid1().__str__()
    replica_set_config = HPA_config
    replica_set_config['instance_name'] = replica_set_instance_name
    replica_set_config['spec'] = dict()
    replica_set_config['spec']['replicas'] = replica_set_config['minReplicas']
    replica_set_config['kind'] = 'ReplicaSet'
    replica_set_config['created_time'] = time.time()
    replica_set_config['last_change_time'] = time.time()
    replica_set_config['isHPA'] = True
    replica_set_config['pod_instances'] = list()
    hpa_list: list = get('hpa_list')
    hpa_list.append(replica_set_instance_name)
    put('hpa_list', hpa_list)
    replica_sets_list: list = get('replica_sets_list')
    replica_sets_list.append(replica_set_instance_name)
    put('replica_sets_list', replica_sets_list)
    put(replica_set_instance_name, replica_set_config)

    return "Successfully create HPA set instance {}".format(replica_set_instance_name), 200


@app.route('/Dns', methods=['GET'])
def get_dns():
    result = dict()
    result['dns_list'] = get('dns_list')
    for dns_instance_name in result['dns_list']:
        dns_instance_config = get(dns_instance_name, assert_exist=False)
        if dns_instance_config:
            result[dns_instance_name] = dns_instance_config
    return json.dumps(result), 200


@app.route('/Dns/Config', methods=['GET'])
def get_dns_config():
    result = get('dns_config')
    return json.dumps(result), 200


@app.route('/Dns/Config', methods=['POST'])
def post_dns_config():
    json_data = request.json
    new_config: dict = json.loads(json_data)
    config: dict = get('dns_config')
    for key, item in new_config.items():
        config[key] = item
    put('dns_config', config)
    return json.dumps(config)


@app.route('/Pod', methods=['POST'])
def post_pods():
    json_data = request.json
    config: dict = json.loads(json_data)
    assert config['kind'] == 'Pod'
    object_name = config['name']
    instance_name = config['name'] + uuid.uuid1().__str__()
    config['instance_name'] = instance_name
    config['status'] = 'Wait for Schedule'
    config['created_time'] = time.time()
    config['strategy'] = config['strategy'] if config.get('strategy') is not None else 'roundrobin'
    # print("create {}".format(instance_name))
    pods_list: list = get('pods_list')
    pods_list.append(instance_name)
    put('pods_list', pods_list)
    put(instance_name, config)
    schedule(config)
    return json.dumps(config), 200


def schedule(config):
    if config['kind'] == 'Pod' and config['status'] == 'Wait for Schedule':
        r = requests.get(url='{}/Node'.format(api_server_url))
        nodes_list = get('nodes_list')
        instance_name = config['instance_name']
        mem_need = parse_bytes(config['mem'])
        config['status'] = 'Schedule Failed'
        if len(nodes_list) == 0:
            print("no node registered !")

        strategy = config['strategy'] if config.get('strategy') is not None else 'roundrobin'
        index_list = list()
        if strategy == 'roundrobin':
            schedule_counts = get('schedule_counts', assert_exist=False)
            if schedule_counts is None or schedule_counts > 10:
                put('schedule_counts', 0)
            else:
                put('schedule_counts', schedule_counts + 1)
            schedule_counts = get('schedule_counts', assert_exist=True)

            index = schedule_counts % len(nodes_list) if len(nodes_list) > 0 else 0
            for i in range(index, len(nodes_list)):
                index_list.append(i)
            for i in range(0, index):
                index_list.append(i)
        elif strategy == 'random':
            for i in range(0, len(nodes_list)):
                index_list.append(i)
            random.shuffle(index_list)
        else:
            logging.warning('strategy not assigned...')
        for i in index_list:
            node_instance_name = nodes_list[i]
            # todo: check node status here
            current_node = get(node_instance_name)
            print("node status = ", current_node['status'])
            if current_node['status'] != 'Running':
                continue
            print("free_memory = {}, need_memory = {}".format(current_node['free_memory'], mem_need))
            if current_node['free_memory'] > mem_need:
                config['node'] = node_instance_name
                config['status'] = 'Ready to Create'
                break
        if config.__contains__('node'):
            print('把 pod {} 调度到节点 {} 上'.format(instance_name, config['node']))
        else:
            print("Schedule failure")
        url = "{}/Pod/{}/create".format(api_server_url, instance_name)
        json_data = json.dumps(config)
        # 向api_server发送调度结果
        r = requests.post(url=url, json=json_data)


@app.route('/ReplicaSet', methods=['POST'])
def upload_replica_set():
    json_data = request.json
    config: dict = json.loads(json_data)
    assert config['kind'] == 'ReplicaSet'
    assert config['spec']['replicas'] > 0
    replica_set_instance_name = config['name'] + uuid.uuid1().__str__()
    config['instance_name'] = replica_set_instance_name
    config['pod_instances'] = list()
    config['created_time'] = time.time()
    replica_sets_list: list = get('replica_sets_list')
    replica_sets_list.append(replica_set_instance_name)
    put('replica_sets_list', replica_sets_list)
    put(replica_set_instance_name, config)
    return "Successfully create replica set instance {}".format(replica_set_instance_name), 200





@app.route('/Service', methods=['POST'])
def upload_service():
    json_data = request.json
    config: dict = json.loads(json_data)
    assert config['kind'] == 'Service'
    service_instance_name = config['name'] + uuid.uuid1().__str__()
    config['instance_name'] = service_instance_name
    config['pod_instances'] = list()
    config['created_time'] = time.time()
    config['status'] = 'Created'
    services_list: list = get('services_list')
    services_list.append(service_instance_name)
    put('services_list', services_list)
    put(service_instance_name, config)
    url = '{}/Service/{}/{}'.format(api_server_url, service_instance_name, 'create')
    utils.post(url=url, config=config)
    return "Successfully create service instance {}".format(service_instance_name), 200


@app.route('/Service/<string:instance_name>/<string:behavior>', methods=['POST'])
def update_service(instance_name: str, behavior: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    if behavior == 'create':
        config['status'] = 'Creating'
    elif behavior == 'update':
        config['status'] = 'Updating'
    elif behavior == 'restart':
        config['status'] = 'Restarting'
    elif behavior == 'running':
        config['status'] = 'Running'
    elif behavior == 'remove':
        config['status'] = 'Removing'
    elif behavior == 'none':
        config['status'] = 'None'
    put(instance_name, config)
    return "Successfully update service instance {}".format(instance_name), 200


@app.route('/Dns', methods=['POST'])
def upload_dns():
    json_data = request.json
    config: dict = json.loads(json_data)
    assert config['kind'] == 'Dns'
    dns_instance_name = config['name'] + uuid.uuid1().__str__()
    config['instance_name'] = dns_instance_name
    config['service_instances'] = list()
    config['created_time'] = time.time()
    dns_list: list = get('dns_list')
    dns_list.append(dns_instance_name)
    put('dns_list', dns_list)
    put(dns_instance_name, config)
    url = "{}/Dns/{}/{}".format(api_server_url, dns_instance_name, 'create')
    utils.post(url=url, config=config)
    return "Successfully create dns instance {}".format(dns_instance_name), 200


@app.route('/Dns/<string:instance_name>/<string:behavior>', methods=['POST'])
def update_dns(instance_name: str, behavior: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    if behavior == 'create':
        config['status'] = 'Creating'
    elif behavior == 'update':
        config['status'] = 'Updating'
    elif behavior == 'restart':
        config['status'] = 'Restarting'
    elif behavior == 'running':
        config['status'] = 'Running'
    elif behavior == 'remove':
        config['status'] = 'Removing'
    elif behavior == 'none':
        config['status'] = 'None'
    put(instance_name, config)
    return "Successfully update dns instance {}".format(instance_name)


@app.route('/ReplicaSet/<string:instance_name>/', methods=['POST'])
def update_replica_set(instance_name: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    config['status'] = 'Creating'
    put(instance_name, config)
    return "Successfully update replica set instance {}".format(instance_name), 200


@app.route('/Pod/<string:instance_name>', methods=['GET'])
def get_pod_instance(instance_name: str):
    return json.dumps(get(instance_name, assert_exist=False))


@app.route('/Pod/<string:instance_name>/<string:behavior>', methods=['POST'])
def post_pod(instance_name: str, behavior: str):
    if behavior == 'create':
        json_data = request.json
        config: dict = json.loads(json_data)
        put(instance_name, config)
        config['behavior'] = 'create'
    elif behavior == 'update':  # update pods information such as ip
        json_data = request.json
        config: dict = json.loads(json_data)
        put(instance_name, config)
        return 'success', 200
    elif behavior == 'remove':
        config = get(instance_name)
        config['status'] = 'Removed'
        put(instance_name, config)
        config['behavior'] = 'remove'
    elif behavior == 'execute':
        config = get(instance_name)
        json_data = request.json
        upload_cmd: dict = json.loads(json_data)
        # if config.get('cmd') is not None and config['cmd'] != upload_cmd['cmd']:
        config['behavior'] = 'execute'
        config['cmd'] = upload_cmd['cmd']
    elif behavior == 'delete':
        pods_list: list = get('pods_list')
        index = -1
        for i, pod_instance_name in enumerate(pods_list):
            if pod_instance_name == instance_name:
                index = i
        pods_list.pop(index)
        delete_key(instance_name)
        put('pods_list', pods_list)
        return "success", 200
    else:
        return json.dumps(dict()), 404
    # todo: post pod information to related node

    worker_url = None
    pods_list = get('pods_list')
    for pod_instance_name in pods_list:
        if instance_name == pod_instance_name:
            pod_config = get(pod_instance_name)
            if pod_config.get('node') is not None:
                node_instance_name = pod_config['node']
                node_config = get(node_instance_name)
                worker_url = node_config['url']
    if worker_url is not None:  # only scheduler successfully will have a worker_url
        r = requests.post(url=worker_url + "/Pod", json=json.dumps(config))
    # broadcast_message('Pod', config.__str__())
    return json.dumps(config), 200


@app.route('/Function', methods=['GET'])
def get_function():
    result = dict()
    result['functions_list'] = get('functions_list')
    for function_name in result['functions_list']:
        result[function_name] = get(function_name)
    return json.dumps(result), 200

@app.route('/Job', methods=['GET'])
def get_job():
    result = dict()
    result['jobs_list'] = get('jobs_list')
    for job_name in result['jobs_list']:
        result[job_name] = get(job_name)
    return json.dumps(result), 200


@app.route('/Job', methods=['POST'])
def upload_job():
    json_data = request.json
    job_config: dict = json.loads(json_data)
    job_name = job_config['name']
    job_config['created_time'] = time.time()
    job_config['status'] = 'Uploaded'
    job_config['files_list'] = list()
    job_config['pod_instances'] = list()
    jobs_list: list = get('jobs_list')
    # node instance name bind with physical mac address
    flag = 0
    for name in jobs_list:
        if name == job_name:
            flag = 1
    if not flag:
        jobs_list.append(job_name)
    else:  # replace the old one
        old_job_config: dict = get(job_name)
        old_pod_instances = old_job_config['pod_instances']
        for old_pod_instance_name in old_pod_instances:
            r = requests.post("{}/Pod/{}/remove".format(api_server_url, old_pod_instance_name))
    put('jobs_list', jobs_list)
    put(job_name, job_config)  # replace the old one if exist
    return json.dumps(get('jobs_list')), 200


@app.route('/Job/<string:instance_name>/<string:behavior>', methods=['POST'])
def handle_job(instance_name: str, behavior: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    if behavior == 'upload_file':
        job_config = get(instance_name, assert_exist=False)
        if job_config is None:
            return "Not found", 404
        file_name = config['file_name']
        file_data = config['file_data']
        files_list: list = job_config['files_list']
        flag = 0
        for name in files_list:
            if name == file_name:
                flag = 1
        if not flag:
            files_list.append(file_name)
        job_config[file_name] = file_data
        put(instance_name, job_config)
    elif behavior == 'delete':
        jobs_list: list = get('jobs_list')
        match_id = -1
        for index, job_name in enumerate(jobs_list):
            if job_name == instance_name:
                match_id = index
                break
        if match_id != -1:   # matched
            job_config = jobs_list[match_id]
            jobs_list.pop(match_id)
            put('jobs_list', jobs_list)
            for pod_instance_name in job_config['pod_instances']:
                r = requests.post("{}/Pod/{}/remove".format(api_server_url, pod_instance_name), json=json.dumps(dict()))
    elif behavior == 'start':
        job_config = get(instance_name, assert_exist=False)
        if job_config is None:
            return 'Not found ', 404
        job_pod_config: dict = job_config.copy()
        job_pod_config['kind'] = 'Pod'
        job_pod_config['isGPU'] = True
        # upload_config.pop('pod_instances')
        r = requests.post("{}/Pod".format(api_server_url), json=json.dumps(job_pod_config))
        if r.status_code == 200:
            pod_config = json.loads(r.content.decode())
            pod_instance_name = pod_config['instance_name']
            job_pod_config['pod_instances'].append(pod_instance_name)
            put(instance_name, job_config)
            # add the pod into the pod_instances list
            return pod_instance_name, 200
        else:
            return "Wait for container build", 300
    elif behavior == 'submit':
        job_config = get(instance_name, assert_exist=False)
        if job_config is None:
            return 'Not found ', 404
        if len(job_config['pod_instances']) < 1:
            return 'Wait for Pod start', 300
        job_config['last_receive_time'] = time.time()
        put(instance_name, job_config)
        if len(job_config['pod_instances']) < 1:
            return 'Not Found', 404
        pod_instance_name = job_config['pod_instances'][0]
        pod_config = get(pod_instance_name)
        pod_config['last_submitted_time'] = time.time()
        put(pod_instance_name, pod_config)
        pod_ip = pod_config['ip']
        pod_url = "http://" + pod_ip + ':5054/submit'
        upload_config = {"module_name": instance_name}
        r = requests.post(pod_url, json=json.dumps(upload_config))
        if r.status_code == 200:
            result = json.loads(r.content.decode())
            return json.dumps(result), 200
        else:
            return "Submit error", 400
    elif behavior == 'download':
        job_config = get(instance_name, assert_exist=False)
        if job_config is None:
            return 'Not found ', 404
        if len(job_config['pod_instances']) < 1:
            return 'Wait for Pod start', 300
        job_config['last_receive_time'] = time.time()
        put(instance_name, job_config)
        pod_instance_name = job_config['pod_instances'][0]
        pod_config = get(pod_instance_name)
        pod_config['last_submitted_time'] = time.time()
        put(pod_instance_name, pod_config)
        pod_ip = pod_config['ip']
        pod_url = "http://" + pod_ip + ':5054/download'
        upload_config = {"module_name": instance_name}
        r = requests.post(pod_url, json=json.dumps(upload_config))
        if r.status_code == 200:
            result = json.loads(r.content.decode())
            return json.dumps(result), 200
        else:
            return "Download error", r.status_code


@app.route('/Function', methods=['POST'])
def upload_function():
    json_data = request.json
    function_config: dict = json.loads(json_data)
    function_name = function_config['name']
    function_config['created_time'] = time.time()
    function_config['status'] = 'Uploaded'
    function_config['requirement_status'] = 'Not Found'
    function_config['pod_instances'] = list()
    # print("node_config = ", node_config)
    functions_list: list = get('functions_list')
    # node instance name bind with physical mac address
    flag = 0
    for name in functions_list:
        if name == function_name:
            flag = 1
    if not flag:
        functions_list.append(function_name)
    else:  # replace the old one
        old_function_config: dict = get(function_name)
        old_pod_instances = old_function_config['pod_instances']
        for old_pod_instance_name in old_pod_instances:
            r = requests.post("{}/Pod/{}/remove".format(api_server_url, old_pod_instance_name))
    put('functions_list', functions_list)
    put(function_name, function_config)  # replace the old one if exist
    return json.dumps(get('functions_list')), 200


def add_function_pod_instance(function_instance_name, function_config: dict):
    upload_config: dict = function_config.copy()
    upload_config['kind'] = 'Pod'
    upload_config['last_activated_time'] = time.time()
    # upload_config.pop('pod_instances')
    r = requests.post("{}/Pod".format(api_server_url), json=json.dumps(upload_config))
    if r.status_code == 200:
        pod_config = json.loads(r.content.decode())
        pod_instance_name = pod_config['instance_name']
        function_config['pod_instances'].append(pod_instance_name)
        put(function_instance_name, function_config)
        # add the pod into the pod_instances list
        return pod_instance_name
    else:
        return None


@app.route('/Function/<string:instance_name>/<string:behavior>', methods=['POST'])
def handle_function(instance_name: str, behavior: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    if behavior == 'upload_requirement':
        function_config = get(instance_name, assert_exist=False)
        if function_config is None:
            return "Not found", 404
        function_config['requirement'] = config['requirement']
        function_config['status'] = 'Uploaded'
        function_config['requirement_status'] = 'Uploaded'
        put(instance_name, function_config)  # replace the old one if exist
    elif behavior == 'delete':
        function_list: list = get('functions_list')
        match_id = -1
        for index, function_name in enumerate(function_list):
            if function_name == instance_name:
                match_id = index
                break
        if match_id != -1:
            function_config = function_list[match_id]
            function_list.pop(match_id)
            put('functions_list', function_list)
            for pod_instance_name in function_config['pod_instances']:
                r = requests.post("{}/Pod/{}/remove".format(api_server_url, pod_instance_name), json=json.dumps(dict()))
    elif behavior == 'start':  # debug only
        function_config = get(instance_name, assert_exist=False)
        if function_config is None:
            return "Not found", 404
        function_config['kind'] = 'Pod'
        r = requests.post("{}/Pod".format(api_server_url), json=json.dumps(function_config))
        return json.dumps(config), 200
    elif behavior == 'activate':
        function_config = get(instance_name, assert_exist=False)
        if function_config is None:
            return 'Not found ', 404
        pod_instances: list = function_config['pod_instances']
        valid_pod_instance_names = list()
        for pod_instance_name in pod_instances:
            pod_instance_config = get(pod_instance_name, assert_exist=False)
            if pod_instance_config:
                if pod_instance_config['status'] == 'Running' and pod_instance_config.__contains__('ip'):
                    valid_pod_instance_names.append(pod_instance_name)
        if len(valid_pod_instance_names) == 0:
            # if no instance exist, cold start
            pod_instance_name = add_function_pod_instance(instance_name, function_config.copy())
            if pod_instance_name:
                valid_pod_instance_names.append(pod_instance_name)
            else:
                return "Serverless Pod build error", 300
        # config is the parameter yaml, which is the context dict
        # random pick
        function_config['last_receive_time'] = time.time()
        put(instance_name, function_config)
        pod_instance_name = valid_pod_instance_names[random.randint(0, len(valid_pod_instance_names) - 1)]
        pod_config = get(pod_instance_name)
        pod_config['last_activated_time'] = time.time()
        put(pod_instance_name, pod_config)
        pod_ip = pod_config['ip']
        context = config
        function_name = context['function_name']
        pod_url = "http://" + pod_ip + ':5052/function/module/{}'.format(function_name)
        r = requests.post(pod_url, json=json.dumps(context))
        if r.status_code == 200:
            result = json.loads(r.content.decode())
            result['ip'] = pod_ip
            return json.dumps(result), 200
        else:
            return "Activate error", 400
    elif behavior == 'add_instance':
        function_config = get(instance_name, assert_exist=False)
        if function_config is None:
            return 'Not found ', 404
        return add_function_pod_instance(instance_name, function_config.copy())


@app.route('/DAG', methods=['GET'])
def get_dags():
    dag_list = get('dag_list')
    result = dict()
    result['dag_list'] = dag_list
    for dag_name in dag_list:
        dag_config = get(dag_name, assert_exist=False)
        if dag_config:
            result[dag_name] = dag_config
    return json.dumps(result), 200


@app.route('/DAG/<string:dag_name>', methods=['GET'])
def get_dag(dag_name: str):
    dag = get(dag_name, assert_exist=False)
    return json.dumps(dag), 200


def build_DAG_from_dict(dag_dict: dict):
    if not dag_dict.__contains__('elements') or not dag_dict.__contains__(
            'branch_condition') or not dag_dict.__contains__('name_data'):
        return None
    elements = dag_dict['elements']
    branch_condition = dag_dict['branch_condition']
    name_data = dag_dict['name_data']
    node_id_to_name_dict = dict()
    for name in name_data:  # ID to real user-defined name
        node_id_to_name_dict[name[0]] = name[1]['label']

    node_list = list()
    node_dict = dict()
    edge_list = list()
    edge_dict = dict()
    for element in elements:
        element_id = element['id']
        if element.__contains__('position'):  # node
            serverless_function = ServerlessFunction.from_dict(element, node_name=node_id_to_name_dict[element_id])
            if serverless_function:
                node_list.append(serverless_function)
                node_dict[element_id] = serverless_function
            else:
                return None
        elif element.__contains__('source'):  # edge
            edge = Edge.from_dict(element, node_dict)
            if edge:
                edge_list.append(edge)
                edge_dict[element_id] = edge
        else:
            return None
    for edge in edge_list:
        print("edge source = {}, target = {}".format(edge.source, edge.target))
        edge.source.add_out_edge(edge)
        edge_index = edge.index
        if branch_condition.__contains__(edge_index):
            edge.update_condition(branch_condition[edge_index])
    my_dag = DAG.from_node_list_and_edge_list(node_list, edge_list)
    for node in node_list:
        print("type = {}, node_name = {}, module = {}, function ={}".format(node.node_type, node.name, node.module_name, node.function_name))
        for edge in node.out_edge:
            print("out node = ", edge.target.name)
    return my_dag


@app.route('/DAG/<string:dag_name>/<string:behavior>', methods=['POST'])
def handle_DAG(dag_name: str, behavior: str):
    if behavior == 'upload':
        elements = json.loads(request.form.get('elements'))
        branch_condition = json.loads(request.form.get('localStorage'))
        name_data = json.loads(request.form.get("flowData"))['value']
        dag_dict = {'elements': elements, 'branch_condition': branch_condition, 'name_data': name_data}
        my_dag = build_DAG_from_dict(dag_dict)  # is not none means no serious error
        if my_dag:
            dag_list: list = get('dag_list')
            flag = 0
            for name in dag_list:
                if name == dag_name:
                    flag = 1
            if not flag:
                dag_list.append(dag_name)
            dag_dict['status'] = 'Uploaded'
            dag_dict['initial_parameter_status'] = 'Not Found'
            dag_dict['initial_parameter'] = dict()
            put('dag_list', dag_list)
            put(dag_name, dag_dict)  # replace the old one
            return "Successfully save dag", 200
        else:
            return "Save DAG Error", 500
    elif behavior == 'upload_initial_parameter':
        initial_parameter: dict = json.loads(request.json)
        dag_config: dict = get(dag_name)
        dag_config['initial_parameter'] = initial_parameter
        dag_config['initial_parameter_status'] = 'Uploaded'
        put(dag_name, dag_config)
    elif behavior == 'run':
        dag_config = get(dag_name)
        my_dag: DAG = build_DAG_from_dict(dag_config)
        start_node = my_dag.start_node
        end_node: ServerlessFunction = my_dag.end_node
        print("my_dag = ", my_dag)

        print("my_dag = ", my_dag)
        current_node = start_node.out_edge[0].target
        prev_node_result = dag_config['initial_parameter']
        while current_node != end_node:
            parameters: dict = prev_node_result
            parameters['function_name'] = current_node.function_name
            print("parameters = ", parameters)
            # first: run the current node and get result
            module_name = current_node.module_name
            function_instance_name = 'serverless-' + current_node.module_name
            r = requests.post('{}/Function/{}/activate'.format(api_server_url, function_instance_name),
                              json=json.dumps(parameters))
            if r.status_code != 200:
                return "{}.{} activation error!".format(module_name, current_node.function_name), 500
            prev_node_result: dict = json.loads(r.content.decode())
            success = 0
            current_out_edge = current_node.out_edge
            for edge in current_out_edge:
                condition = edge.condition
                print("try to eval condition = ", condition)
                if eval(condition):
                    success = 1
                    current_node = edge.target
                    break
            if success == 0:
                return "Not node match the condition! ", 500
        return json.dumps(prev_node_result), 200


@app.route('/heartbeat', methods=['POST'])
def receive_heartbeat():
    # 收到node发送的心跳包
    json_data = request.json
    heartbeat: dict = json.loads(json_data)
    heartbeat['last_receive_time'] = time.time()
    node_instance_name = heartbeat['instance_name']
    # node_config = get(node_instance_name)
    # if node_config['status'] == 'Not Available':
    #     # we get the heartbeat of a lost node again
    #     node_config['status'] = 'Running'
    for pod_instance_name in heartbeat['pod_instances']:
        pod_heartbeat = heartbeat[pod_instance_name]
        pod_config = get(pod_instance_name, assert_exist=False)
        if pod_config:
            if pod_config['status'] != 'Removed':
                pod_config['status'] = pod_heartbeat['status']
            pod_config['cpu_usage_percent'] = pod_heartbeat['cpu_usage_percent']
            pod_config['memory_usage_percent'] = pod_heartbeat['memory_usage_percent']
            pod_config['ip'] = pod_heartbeat['ip']
            pod_config['volume'] = pod_heartbeat['volume']
            pod_config['ports'] = pod_heartbeat['ports']
            pod_config['node'] = node_instance_name
            pod_config['container_names'] = pod_heartbeat['container_names']
            put(pod_instance_name, pod_config)
        heartbeat.pop(pod_instance_name)  # the information is of no use
    nodes_list = get('nodes_list')
    flag = 0
    for name in nodes_list:
        if name == node_instance_name:
            flag = 1
    if not flag:
        nodes_list.append(node_instance_name)
    put('nodes_list', nodes_list)
    put(node_instance_name, heartbeat)
    return json.dumps(heartbeat), 200


def main():
    init_api_server()
    app.run(host='0.0.0.0', port=5050, processes=True)


if __name__ == '__main__':
    main()
