import ast
import copy
import datetime
from typing import List

import yaml.parser
from flask import Flask, redirect, url_for, request, jsonify, Response
from flask_cors import CORS
import base64
import os
import json
import pika
import uuid
import etcd3
import entities
import re

total_memory = 5 * 1024 * 1024 * 1024
app = Flask(__name__)
# CORS(app, supports_credentials=True)
etcd = etcd3.client()
nodes = {'node1': {'pods': {}, 'ReplicaSets': {}, 'cpu': 12, 'mem': total_memory,
                   'heartbeat_time': datetime.datetime.now().second},
         'node2': {'pods': {}, 'ReplicaSets': {}, 'cpu': 12, 'mem': total_memory,
                   'heartbeat_time': datetime.datetime.now().second}}
#         nodename:{
#         'pods':{podname:config},              //config中的['spec']['replicas']是该node中应该跑的数量，在心跳包发来时如果发现实际数量少于应该的数量，则向node发送重新启动相应数量的请求
#         'ReplicaSets':{ReplicaSetname:config},//config中的['spec']['replicas']是该node中应该跑的数量，在心跳包发来时如果发现实际数量少于应该的数量，则向node发送重新启动相应数量的请求
#         'cpu':,                               //这里的cpu和mem只由心跳包更新，是node的定义资源可用
#         'mem':,
#         'heartbeat_time':
#         }
rescale = {'node1': {'pods': {}, 'ReplicaSets': {}}, 'node2': {'pods': {}, 'ReplicaSets': {}}}
pods = {}
#       podname:config                          //config中的['spec']['replicas']是所有node中应该跑的总数
ReplicaSets = {}


#       ReplicaSetname:config                   //config中的['spec']['replicas']是所有node中应该跑的总数

def upgrade_etcd():
    etcd.put('nodes', str(nodes))
    etcd.put('pods', str(pods))
    etcd.put('ReplicaSets', str(ReplicaSets))


upgrade_etcd()


def broadcast_message(channel_name: str, message: str):
    connect = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connect.channel()
    # declare the name and type of the channel
    channel.exchange_declare(exchange=channel_name, exchange_type="fanout")
    # broadcast the message
    channel.basic_publish(exchange=channel_name, routing_key='', body=message.encode())
    connect.close()


def nodes_check():
    # 检查是否存在node crash和replicaset数量是否正确，目前没有整合进去,需要放进service
    # 检查是否存在node crash
    time_now = datetime.datetime.now().second
    nodes_for_del = []
    pods_for_restart = {}
    ReplicaSets_for_restart = {}
    for node in nodes:
        last_check_time = nodes[node]['heartbeat_time']
        if time_now - last_check_time > 10:
            nodes_for_del.append(node)
            pods_in_node = copy.deepcopy(nodes[node]['pods'])
            ReplicaSets_in_node = copy.deepcopy(nodes[node]['ReplicaSets'])
            for pod in pods_in_node:
                if pods_for_restart.__contains__(pod):
                    pods_for_restart[pod]['spec']['replicas'] += pods_in_node[pod]['spec']['replicas']
                else:
                    pods_for_restart[pod] = pods_in_node[pod]
            for ReplicaSet in ReplicaSets_in_node:
                if ReplicaSets_for_restart.__contains__(ReplicaSet):
                    ReplicaSets_for_restart[ReplicaSet]['spec']['replicas'] += ReplicaSets_in_node[ReplicaSet]['spec'][
                        'replicas']
                else:
                    ReplicaSets_for_restart[ReplicaSet] = ReplicaSets_in_node[ReplicaSet]
    for node in nodes_for_del:
        del nodes[node]
    # 将pods和ReplicaSets分给剩下的nodes
    msg = {'kind': 'reschedule', 'pods': pods_for_restart, 'ReplicaSets': ReplicaSets_for_restart, 'nodes': nodes}
    broadcast_message('pods', msg.__str__())


def config_set(config1, config2):
    # 用config2修正config1的cpu和mem以及containers的资源
    config1['cpu'] = config2['cpu']
    config1['mem'] = config2['mem']
    for container in config2['containers']:
        for con in config1['containers']:
            if con['name'] == container['name']:
                if container['resource'].__contains__('cpu'):
                    con['resource']['cpu'] = container['resource']['cpu']
                if container['resource'].__contains__('mem'):
                    con['resource']['mem'] = container['resource']['mem']
                break


# pods ReplicaSets均是在第一次收到时修改pods ReplicaSets，第二次收到时修改nodes
# HorizontalPodAutoscaler在第二次收到时修改pods ReplicaSets nodes
# reschedule不需要修改pods和ReplicaSets，只修改nodes
@app.route('/pods', methods=['GET', 'POST'])
def get_pods():
    if request.method == 'GET':
        # 网页获取
        return json.dumps(nodes), 200
    elif request.method == 'POST':
        # 通过yaml起pod或Replicaset
        json_data = request.json
        config: dict = json.loads(json_data)
        instance_name = config['name'] + uuid.uuid1().__str__()
        config['instance_name'] = instance_name
        print("create {}".format(instance_name))
        # 将nodes情况告诉scheduler以方便调度
        config['nodes'] = nodes
        if config['kind'] == 'pod':
            config['spec'] = {'replicas': 1}
            pods[config['name']] = config
        if config['kind'] == 'ReplicaSet':
            ReplicaSets[config['name']] = config
        # 如果是扩容文件，则将原config文件也放进去方便kubelet依此扩容
        if config['kind'] == 'HorizontalPodAutoscaler':
            # config['config']中的['spec']['replicas']是所有node中应该跑的总数，即现有总数
            if config['prekind'] == 'pod':
                config_set(pods[config['name']], config)
                config['config'] = pods[config['name']]
            if config['prekind'] == 'ReplicaSet':
                config_set(ReplicaSets[config['name']], config)
                config['config'] = ReplicaSets[config['name']]
        broadcast_message('pods', config.__str__())
        # etcd更新
        upgrade_etcd()
        return "Successfully create instance {}".format(instance_name), 200


@app.route('/pods/<string:instance_name>', methods=['POST'])
def post_pod(instance_name: str):
    # 将调度结果发给所有nodes
    json_data = request.json
    config: dict = json.loads(json_data)
    # 前两个若nodes的node中已经存在该config，则只会修改nodes里config的['spec']['replicas']值
    if config['kind'] == 'pod':
        print("send create pod msg to {}".format(config['node']))
        if config.__contains__('nodes'):
            del config['nodes']
        if nodes[config['node']]['pods'].__contains__(config['name']):
            # 说明是reschedule
            nodes[config['node']]['pods'][config['name']]['spec']['replicas'] += config['spec']['replicas']
        else:
            nodes[config['node']]['pods'][config['name']] = config
        nodes[config['node']]['mem'] -= entities.parse_bytes(config['mem']) * config['spec']['replicas']
        nodes[config['node']]['cpu'] -= config['cpu'] * config['spec']['replicas']
        # 发送
        broadcast_message('pods', config.__str__())
    if config['kind'] == 'ReplicaSet':
        print("send create ReplicaSet msg to {}".format(config['node']))
        if config.__contains__('nodes'):
            del config['nodes']
        if nodes[config['node']]['ReplicaSets'].__contains__(config['name']):
            # 说明是reschedule
            nodes[config['node']]['ReplicaSets'][config['name']]['spec']['replicas'] += config['spec']['replicas']
        else:
            nodes[config['node']]['ReplicaSets'][config['name']] = config
        nodes[config['node']]['mem'] -= entities.parse_bytes(config['mem']) * config['spec']['replicas']
        nodes[config['node']]['cpu'] -= config['cpu'] * config['spec']['replicas']
        # 发送
        broadcast_message('pods', config.__str__())
    if config['kind'] == 'delete':
        if config['target_kind'] == 'pod':
            pods[config['target_name']]['spec']['replicas'] -= config['num']
            nodes[config['node']]['cpu'] += config['num'] * nodes[config['node']]['pods'][config['target_name']]['cpu']
            nodes[config['node']]['mem'] += config['num'] * entities.parse_bytes(
                nodes[config['node']]['pods'][config['target_name']]['mem'])
            if pods[config['target_name']]['spec']['replicas'] == 0:
                del pods[config['target_name']]
            nodes[config['node']]['pods'][config['target_name']]['spec']['replicas'] -= config['num']
            if nodes[config['node']]['pods'][config['target_name']]['spec']['replicas'] == 0:
                del nodes[config['node']]['pods'][config['target_name']]
        if config['target_kind'] == 'ReplicaSet':
            ReplicaSets[config['target_name']]['spec']['replicas'] -= config['num']
            nodes[config['node']]['cpu'] += config['num'] * nodes[config['node']]['ReplicaSets'][config['target_name']][
                'cpu']
            nodes[config['node']]['mem'] += config['num'] * entities.parse_bytes(
                nodes[config['node']]['ReplicaSets'][config['target_name']]['mem'])
            if ReplicaSets[config['target_name']]['spec']['replicas'] == 0:
                del ReplicaSets[config['target_name']]
            nodes[config['node']]['ReplicaSets'][config['target_name']]['spec']['replicas'] -= config['num']
            if nodes[config['node']]['ReplicaSets'][config['target_name']]['spec']['replicas'] == 0:
                del nodes[config['node']]['pods'][config['target_name']]
        # 发送
        broadcast_message('pods', config.__str__())
    if config['kind'] == 'HorizontalPodAutoscaler':
        print("send HorizontalPodAutoscaler msg to {}".format(config['node']))
        if config.__contains__('nodes'):
            del config['nodes']
        broadcast_message('pods', config.__str__())
    # etcd更新
    upgrade_etcd()
    return json.dumps(config), 200

class Node(object):
    def __init__(self, index, name, node_type, module_name=None, function_name=None):
        self.index = index
        self.name = name
        self.node_type = node_type
        self.module_name = module_name
        self.function_name = function_name
        self.out_edge = list()
        print(self.__str__())

    @staticmethod
    def from_dict(init_dict: dict, node_name):
        node_id = init_dict['id']
        node_type = init_dict['type']

        if node_type == 'input' or node_type == 'output':
            return Node(node_id, node_name, node_type)
        else:
            match_ = re.fullmatch(r'(\w*)\.(\w*)', node_name.strip(), re.I)
            if match_:
                module_name = match_.group(1)
                function_name = match_.group(2)
                print("module_name = {}".format(module_name))
                print("function_name = {}".format(function_name))
                return Node(node_id, node_name, node_type, module_name, function_name)
            else:
                print("match error")
                return None

    def add_out_edge(self, edge):
        self.out_edge.append(edge)

    def __str__(self):
        return {'index': self.index, 'name': self.name, 'node_type': self.node_type, 'module_name': self.module_name, 'function_name': self.function_name, 'out_edge': self.out_edge}.__str__()

class Edge(object):
    def __init__(self, index, source, target, condition="True"):
        self.index = index
        self.source = source
        self.target = target
        self.condition = condition

    @staticmethod
    def from_dict(init_dict: dict, nodes: dict):
        edge_id = init_dict['id']
        source_node_id = init_dict['source']
        target_node_id = init_dict['target']
        if nodes.__contains__(source_node_id) and nodes.__contains__(target_node_id):
            return Edge(edge_id, nodes[source_node_id], nodes[source_node_id], "True")
        else:
            return None

    def update_condition(self, condition:str):
        self.condition = condition
        print("Edge {} condition updated! {}".format(self.index, self.condition))

    def __str__(self):
        return {'index': self.index, 'source': self.source, 'target': self.target, 'condition': self.condition}.__str__()

class DAG(object):
    def __init__(self, start_node: Node, end_node: Node, node_list: List[Node], edge_list: List[Edge]):
        self.start_node = start_node
        self.end_node = end_node
        self.node_list = node_list
        self.edge_list = edge_list

    @staticmethod
    def from_node_list_and_edge_list(node_list: List[Node], edge_list: List[Edge]):
        start_node = None
        end_node = None
        for node in node_list:
            if node.node_type == 'input':
                start_node = node
            if node.node_type == 'output':
                end_node = node
        if start_node and end_node:
            return DAG(start_node, end_node, node_list, edge_list)
        else:
            return None

    def node_size(self):
        return len(self.node_list)

    def edge_size(self):
        return len(self.edge_list)

    def __str__(self):
        return {'start_node': self.start_node, 'end_node': self.end_node, 'node_list': self.node_list, 'edge_list': self.edge_list}.__str__()

@app.route('/DAG/<string:DAG_name>', methods=['GET'])
def get_dag(DAG_name: str):
    if not use_etcd:
        if etcd_supplant.__contains__(DAG_name):
            return etcd_supplant[DAG_name].__str__(), 200
        else:
            return "DAG not found!", 404
    else:
        raise NotImplementedError

@app.route('/DAG/<string:DAG_name>', methods=['POST'])
def upload(DAG_name: str):
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
        if element.__contains__('position'):    # node
            node = Node.from_dict(element, node_name=name_dict[element_id])
            if node:
                node_list.append(node)
                node_dict[element_id] = node
            else:
                return "Node match error", 404
        elif element.__contains__('source'):   # edge
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
            print("Save DAG {}".format(DAG_name))
            etcd_supplant[DAG_name] = my_dag
        else:
            raise NotImplementedError
        return "Successfully built a DAG with {} nodes and {} edges".format(my_dag.node_size(), my_dag.edge_size()), 200
    else:
        return "Built DAG failure", 404


@app.route('/rescale', methods=['POST'])
def rescale_update():
    json_data = request.json
    msg: dict = json.loads(json_data)
    if msg['kind'] == 'pod':
        print('{} add one pod replica {}'.format(msg['node'], msg['name']))
        if rescale[msg['node']]['pods'].__contains__(msg['name']):
            rescale[msg['node']]['pods'][msg['name']] += 1
        else:
            rescale[msg['node']]['pods'][msg['name']] = 1
    if msg['kind'] == 'ReplicaSet':
        print('{} add one ReplicaSet replica {}'.format(msg['node'], msg['name']))
        if rescale[msg['node']]['ReplicaSets'].__contains__(msg['name']):
            rescale[msg['node']]['ReplicaSets'][msg['name']] += 1
        else:
            rescale[msg['node']]['ReplicaSets'][msg['name']] = 1


@app.route('/heartbeat', methods=['POST'])
def receive_heartbeat():
    # 收到node发送的心跳包
    json_data = request.json
    heartbeat: dict = json.loads(json_data)
    node_name = heartbeat['node']
    # 更新内存检查资源和时间
    nodes[node_name]['cpu'] = heartbeat['cpu']
    nodes[node_name]['mem'] = heartbeat['mem']
    nodes[node_name]['heartbeat_time'] = datetime.datetime.now().second
    # 检查数量，发现数量少于应有数量，向node发送重新启动相应数量的请求
    node_pods = heartbeat['pods']
    node_ReplicaSets = heartbeat['ReplicaSets']
    # 从内存里拿config
    for pod in node_pods:
        if node_pods[pod] < nodes[node_name]['pods'][pod]['spec']['replicas']:
            num_for_recreate = nodes[node_name]['pods'][pod]['spec']['replicas'] - node_pods[pod]
            config = copy.deepcopy(nodes[node_name]['pods'][pod])
            config['spec']['replicas'] = num_for_recreate
            config['node'] = node_name
            broadcast_message('pods', config.__str__())
    for ReplicaSet in node_ReplicaSets:
        if node_ReplicaSets[ReplicaSet] < nodes[node_name]['ReplicaSets'][ReplicaSet]['spec']['replicas']:
            num_for_recreate = nodes[node_name]['ReplicaSets'][ReplicaSet]['spec']['replicas'] - node_ReplicaSets[
                ReplicaSet]
            config = copy.deepcopy(nodes[node_name]['ReplicaSets'][ReplicaSet])
            config['spec']['replicas'] = num_for_recreate
            config['node'] = node_name
            broadcast_message('pods', config.__str__())
            del config
    return json.dumps(heartbeat), 200


if __name__ == '__main__':
    if etcd.get('nodes')[0] is not None:
        nodes = ast.literal_eval(str(etcd.get('nodes')[0], 'UTF-8'))
        pods = ast.literal_eval(str(etcd.get('pods')[0], 'UTF-8'))
        ReplicaSets = ast.literal_eval(str(etcd.get('ReplicaSets')[0], 'UTF-8'))
    app.run(port=5050, processes=True)
