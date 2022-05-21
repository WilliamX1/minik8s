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
from serverless import Node, Edge, DAG

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



@app.route('/DAG/<string:dag_name>', methods=['GET'])
def get_dag(dag_name: str):
    if not use_etcd:
        if etcd_supplant.__contains__(dag_name):
            return etcd_supplant[dag_name].__str__(), 200
        else:
            return "DAG not found!", 404
    else:
        raise NotImplementedError

@app.route('DAG/run/<string:dag_name>', methods=['GET'])
def run_DAG(dag_name: str):
    my_dag: DAG = etcd_supplant[dag_name]
    current_node = start_node = my_dag.start_node
    end_node: Node = my_dag.end_node
    while current_node != end_node:
        result = current_

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
            print("Save DAG {}".format(dag_name))
            etcd_supplant[dag_name] = my_dag
        else:
            raise NotImplementedError
        return "Successfully built a DAG with {} nodes and {} edges".format(my_dag.node_size(), my_dag.edge_size()), 200
    else:
        return "Built DAG failure", 404


if __name__ == '__main__':
    app.run(port=5050, processes=True)
