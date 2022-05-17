from typing import List

import yaml.parser
from flask import Flask, redirect, url_for, request, jsonify, Response
from flask_cors import CORS
import base64
import os
import json
import pika
import uuid
import re

app = Flask(__name__)
# CORS(app, supports_credentials=True)
use_etcd = False
etcd_supplant = dict()


def broadcast_message(channel_name: str, message: str):
    connect = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connect.channel()
    # declare the name and type of the channel
    channel.exchange_declare(exchange=channel_name, exchange_type="fanout")
    # broadcast the message
    channel.basic_publish(exchange=channel_name, routing_key='', body=message.encode())
    connect.close()


@app.route('/pods', methods=['GET', 'POST'])
def get_pods():
    if request.method == 'GET':
        if use_etcd:
            return "Not implemented", 404
        else:
            return json.dumps(etcd_supplant), 200
    elif request.method == 'POST':
        json_data = request.json
        config: dict = json.loads(json_data)
        instance_name = config['name'] + uuid.uuid1().__str__()
        config['instance_name'] = instance_name
        if use_etcd:
            return "Not implemented", 404
        else:
            etcd_supplant[instance_name] = config
            print("create {}".format(instance_name))

        broadcast_message('pods', config.__str__())
        return "Successfully create instance {}".format(instance_name), 200



@app.route('/pods/<string:instance_name>', methods=['POST'])
def post_pod(instance_name: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    if use_etcd:
        return "Not implemented", 404
    else:
        if etcd_supplant.__contains__(instance_name):
            for key in config.keys():
                print("update {}[{}]".format(instance_name, key))
                etcd_supplant[instance_name][key] = config[key]
        else:
            return "Instance Not Fount", 404

    broadcast_message('pods', config.__str__())
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


if __name__ == '__main__':
    app.run(port=5050, processes=True)
