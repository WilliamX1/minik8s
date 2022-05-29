import copy
import time
from flask import Flask, redirect, url_for, request, jsonify, Response
import json
import pika
import uuid
import etcd3

import const
import utils
from serverless import ServerlessFunction, Edge, DAG

app = Flask(__name__)
# CORS(app, supports_credentials=True)

use_etcd = const.use_etcd
etcd = etcd3.client()
etcd_supplant = {'nodes_list': list(), 'pods_list': list(),
                 'services_list': list(), 'replica_sets_list': list(),
                 'dns_list': list(),
                 'dns_config': dict(),  # used for dns
                 }


api_server_url = const.api_server_url


def broadcast_message(channel_name: str, message: str):
    connect = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connect.channel()
    # declare the name and type of the channel
    channel.exchange_declare(exchange=channel_name, exchange_type="fanout")
    # broadcast the message
    channel.basic_publish(exchange=channel_name, routing_key='', body=message.encode())
    connect.close()


@app.route('/Node', methods=['GET'])
def handle_nodes():
    if use_etcd:
        return "not implemented"
    else:
        result = dict()
        result['nodes_list'] = etcd_supplant['nodes_list']
        for node_instance_name in result['nodes_list']:
            result[node_instance_name] = etcd_supplant[node_instance_name]
        return json.dumps(result)


@app.route('/Node', methods=['POST'])
def upload_nodes():
    json_data = request.json
    node_config: dict = json.loads(json_data)
    node_instance_name = node_config['instance_name']
    node_config['last_receive_time'] = time.time()
    node_config['status'] = 'READY TO START'

    print("node_config = ", node_config)
    etcd_supplant['nodes_list'].append(node_instance_name)
    etcd_supplant[node_instance_name] = node_config
    return json.dumps(etcd_supplant['nodes_list']), 200


@app.route('/Node/<string:instance_name>', methods=['DELETE'])
def delete_node(instance_name: str):
    for i in range(len(etcd_supplant['nodes_list'])):
        if etcd_supplant['nodes_list'][i] == instance_name:
            etcd_supplant['nodes_list'].pop(i)
    etcd_supplant[instance_name]['status'] = 'Not Available'
    for pod_instance_name in etcd_supplant['pods_list']:
        if etcd_supplant[pod_instance_name].__contains__('node') and \
                etcd_supplant[pod_instance_name]['node'] == instance_name:
            etcd_supplant[pod_instance_name]['status'] = 'Lost Connect'
    print("Remove node {}".format(instance_name))
    return json.dumps(etcd_supplant['nodes_list']), 200


@app.route('/', methods=['GET'])
def get_all():
    return json.dumps(etcd_supplant), 200


@app.route('/Pod', methods=['GET'])
def get_pods():
    result = dict()
    result['pods_list'] = etcd_supplant['pods_list']
    for pod_instance_name in etcd_supplant['pods_list']:
        if etcd_supplant.__contains__(pod_instance_name):
            result[pod_instance_name] = etcd_supplant[pod_instance_name]
    return json.dumps(result), 200


@app.route('/Service', methods=['GET'])
def get_services():
    result = dict()
    result['services_list'] = etcd_supplant['services_list']
    for service_instance_name in result['services_list']:
        if etcd_supplant.__contains__(service_instance_name):
            result[service_instance_name] = etcd_supplant[service_instance_name]
    return json.dumps(result), 200


@app.route('/Dns', methods=['GET'])
def get_dns():
    result = dict()
    result['dns_list'] = etcd_supplant['dns_list']
    for dns_instance_name in result['dns_list']:
        if etcd_supplant.__contains__(dns_instance_name):
            result[dns_instance_name] = etcd_supplant[dns_instance_name]
    return json.dumps(result), 200


@app.route('/Dns/Config', methods=['GET'])
def get_dns_config():
    result = etcd_supplant['dns_config']
    return json.dumps(result), 200


@app.route('/Dns/Config', methods=['POST'])
def post_dns_config():
    json_data = request.json
    config: dict = json.loads(json_data)
    for key, item in config.items():
        etcd_supplant['dns_config'][key] = item
    return "Successfully changed DNS Config", 200


@app.route('/ReplicaSet', methods=['GET'])
def get_replica_set():
    result = dict()
    result['replica_sets_list'] = etcd_supplant['replica_sets_list']
    for replica_set_instance in result['replica_sets_list']:
        config = etcd_supplant[replica_set_instance]
        result[replica_set_instance] = config
        for pod_instance_name in config['pod_instances']:
            if etcd_supplant.__contains__(pod_instance_name):
                result[pod_instance_name] = etcd_supplant[pod_instance_name]
    print(result)
    return json.dumps(result), 200


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
    print("create {}".format(instance_name))
    etcd_supplant['pods_list'].append(instance_name)
    etcd_supplant[instance_name] = config
    # print("BroadCast_Message Pod")
    broadcast_message('Pod', config.__str__())
    return json.dumps(config), 200


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
    etcd_supplant['replica_sets_list'].append(replica_set_instance_name)
    etcd_supplant[replica_set_instance_name] = config
    # broadcast_message('ReplicaSet', config.__str__())
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
    etcd_supplant['services_list'].append(service_instance_name)
    etcd_supplant[service_instance_name] = config
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
    etcd_supplant[instance_name] = config
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
    etcd_supplant['dns_list'].append(dns_instance_name)
    etcd_supplant[dns_instance_name] = config
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
    elif behavior == 'running':
        config['status'] = 'Running'
    elif behavior == 'remove':
        config['status'] = 'Removing'
    elif behavior == 'none':
        config['status'] = 'None'
    etcd_supplant[instance_name] = config
    return "Successfully update dns instance {}".format(instance_name)


@app.route('/ReplicaSet/<string:instance_name>/', methods=['POST'])
def update_replica_set(instance_name: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    etcd_supplant[instance_name] = config
    return "Successfully update replica set instance {}".format(instance_name), 200


@app.route('/Pod/<string:instance_name>/<string:behavior>', methods=['POST'])
def post_pod(instance_name: str, behavior: str):
    if behavior == 'create':
        json_data = request.json
        config: dict = json.loads(json_data)
        etcd_supplant[instance_name] = copy.deepcopy(config)
        config['behavior'] = 'create'
    elif behavior == 'remove':
        etcd_supplant[instance_name]['status'] = 'Removed'
        config = copy.deepcopy(etcd_supplant[instance_name])
        config['behavior'] = 'remove'
    elif behavior == 'execute':
        config = copy.deepcopy(etcd_supplant[instance_name])
        json_data = request.json
        upload_cmd: dict = json.loads(json_data)
        # if config.get('cmd') is not None and config['cmd'] != upload_cmd['cmd']:
        config['behavior'] = 'execute'
        config['cmd'] = upload_cmd['cmd']
    elif behavior == 'delete':
        # delete the config
        index = -1
        for i in range(len(etcd_supplant['pods_list'])):
            if instance_name == etcd_supplant['pods_list'][i]:
                index = i
                break
        if index != -1:
            etcd_supplant['pods_list'].pop(index)
        etcd_supplant.pop(instance_name)
        return json.dumps(dict()), 200
    else:
        return json.dumps(dict()), 404
    broadcast_message('Pod', config.__str__())
    return json.dumps(config), 200


@app.route('/DAG/<string:dag_name>', methods=['GET'])
def get_dag(dag_name: str):
    if not use_etcd:
        if etcd_supplant.__contains__(dag_name):
            return etcd_supplant[dag_name].__str__(), 200
        else:
            return "DAG not found!", 404
    else:
        raise NotImplementedError


def run_serverless_function(serverless_function: ServerlessFunction):
    pass


@app.route('/DAG/run/<string:dag_name>', methods=['GET'])
def run_DAG(dag_name: str):
    my_dag: DAG = etcd_supplant[dag_name]
    current_node = start_node = my_dag.start_node
    end_node: ServerlessFunction = my_dag.end_node
    while current_node != end_node:
        # result = current_
        pass
    return "not"


@app.route('/DAG/<string:DAG_name>', methods=['POST'])
def upload(dag_name: str):
    elements = json.loads(request.form.get('elements'))
    branch_condition = json.loads(request.form.get('localStorage'))
    name_data = json.loads(request.form.get("flowData"))['value']
    # print("elements = {}".format(elements))
    # print("branch_condition = {}".format(branch_condition))
    # print("name_data = {}".format(name_data))
    name_dict = dict()
    for name in name_data:
        name_dict[name[0]] = name[1]['label']
        # print("name_dict[{}] = {}".format(name[0], name[1]['label']))

    node_list = list()
    node_dict = dict()
    edge_list = list()
    edge_dict = dict()
    for element in elements:
        element_id = element['id']
        if element.__contains__('position'):  # node
            serverless_function = ServerlessFunction.from_dict(element, node_name=name_dict[element_id])
            if serverless_function:
                node_list.append(serverless_function)
                node_dict[element_id] = serverless_function
            else:
                return "Node match error", 404
        elif element.__contains__('source'):  # edge
            edge = Edge.from_dict(element, node_dict)
            if edge:
                edge_list.append(edge)
                edge_dict[element_id] = edge
        else:
            return "error", 404
    for edge in edge_list:
        edge_index = edge.index
        if branch_condition.__contains__(edge_index):
            edge.update_condition(branch_condition[edge_index])
    my_dag = DAG.from_node_list_and_edge_list(node_list, edge_list)
    if my_dag:
        if not use_etcd:
            print("Save DAG {}".format(dag_name))
            etcd_supplant[dag_name] = my_dag
        else:
            raise NotImplementedError
        return "Successfully built a DAG with {} nodes and {} edges".format(my_dag.node_size(), my_dag.edge_size()), 200
    else:
        return "Built DAG failure", 404


@app.route('/heartbeat', methods=['POST'])
def receive_heartbeat():
    # 收到node发送的心跳包
    json_data = request.json
    heartbeat: dict = json.loads(json_data)
    heartbeat['last_receive_time'] = time.time()
    node_instance_name = heartbeat['instance_name']
    if etcd_supplant[node_instance_name]['status'] == 'Not Available':
        # we get the heartbeat of a lost node again
        etcd_supplant['nodes_list'].append(node_instance_name)
        etcd_supplant[node_instance_name]['status'] = 'Running'

    for pod_instance_name in heartbeat['pod_instances']:
        pod_heartbeat = heartbeat[pod_instance_name]
        if etcd_supplant[pod_instance_name]['status'] != 'Removed':
            # if removed before a heartbeat, we do not change the status
            etcd_supplant[pod_instance_name]['status'] = pod_heartbeat['status']
        etcd_supplant[pod_instance_name]['cpu_usage_percent'] = pod_heartbeat['cpu_usage_percent']
        etcd_supplant[pod_instance_name]['memory_usage_percent'] = pod_heartbeat['memory_usage_percent']
        etcd_supplant[pod_instance_name]['ip'] = pod_heartbeat['ip']
        etcd_supplant[pod_instance_name]['node'] = node_instance_name
        heartbeat.pop(pod_instance_name)
    etcd_supplant[node_instance_name] = heartbeat
    return json.dumps(heartbeat), 200


def main():
    app.run(port=5050, processes=True)


if __name__ == '__main__':
    main()
