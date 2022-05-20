import ast
import copy
import datetime
import yaml.parser
from flask import Flask, redirect, url_for, request, jsonify, Response
from flask_cors import CORS
import base64
import os
import json
import pika
import uuid
import etcd3

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


# +++++++++++++++++
def nodes_check():
    # 检查是否存在node crash和replicaset数量是否正确，目前没有整合进去
    # 检查是否存在node crash
    time_now = datetime.datetime.now().second
    nodes_for_del = []
    pods_for_restart = {}
    ReplicaSets_for_restart = {}
    for node in nodes:
        last_check_time = nodes[node]['heartbeat_time']
        if time_now - last_check_time > 10:
            nodes_for_del.append(node)
            pods_for_restart.update(nodes[node]['pods'])
            ReplicaSets_for_restart.update(nodes[node]['ReplicaSets'])
    for node in nodes_for_del:
        del nodes[node]
    # 将pods和ReplicaSets分给剩下的nodes
    # pod因为逻辑的特殊性需要加一个'reschedule'字段方便schedule判断，ReplicaSet则不用
    for pod in pods_for_restart:
        pods_for_restart[pod][nodes] = nodes
        pods_for_restart[pod]['reschedule'] = pods_for_restart[pod]['spec']['replicas']
        del pods_for_restart[pod]['node']
        broadcast_message('pods', pods_for_restart[pod].__str__())
    for ReplicaSet in ReplicaSets_for_restart:
        ReplicaSets_for_restart[ReplicaSet][nodes] = nodes
        del ReplicaSets_for_restart[ReplicaSet]['node']
        broadcast_message('pods', ReplicaSets_for_restart[ReplicaSet].__str__())

def config_set(config1, config2):
    # 用config2修正config1
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
                print('new config')
                print(pods[config['name']])
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
    if config['kind'] == 'pod':
        print("send create pod msg to {}".format(config['node']))
        # 内存更新
        del config['nodes']
        nodes[config['node']]['pods'][config['name']] = config
        # 发送
        broadcast_message('pods', config.__str__())
    if config['kind'] == 'ReplicaSet':
        print("send create ReplicaSet msg to {}".format(config['node']))
        # 内存更新
        del config['nodes']
        nodes[config['node']]['ReplicaSets'][config['name']] = config
        # 发送
        broadcast_message('pods', config.__str__())
    if config['kind'] == 'HorizontalPodAutoscaler':
        print("send HorizontalPodAutoscaler msg to {}".format(config['node']))
        del config['nodes']
        if config['prekind'] == 'pod':
            if not nodes[config['node']]['pods'].__contains__(config['name']):
                nodes[config['node']]['pods'][config['name']] = config['config']
            else:
                nodes[config['node']]['pods'][config['name']]['spec']['replicas'] += config['config']['spec']['replicas']
            pods[config['name']]['spec']['replicas'] += config['config']['spec']['replicas']
        if config['prekind'] == 'ReplicaSet':
            if not nodes[config['node']]['ReplicaSets'].__contains__(config['name']):
                nodes[config['node']]['ReplicaSets'][config['name']] = config['config']
            else:
                nodes[config['node']]['ReplicaSets'][config['name']]['spec']['replicas'] += config['config']['spec']['replicas']
            ReplicaSets[config['name']]['spec']['replicas'] += config['config']['spec']['replicas']
        broadcast_message('pods', config.__str__())
    # etcd更新
    upgrade_etcd()
    return json.dumps(config), 200


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
    # +++++++++++++++++
    # 检查数量，发现数量少于应有数量，向node发送重新启动相应数量的请求
    node_pods = heartbeat['pods']
    node_ReplicaSets = heartbeat['ReplicaSets']
    for pod in node_pods:
        if node_pods[pod] < nodes[node_name]['pods'][pod]['spec']['replicas']:
            num_for_recreate = nodes[node_name]['pods'][pod]['spec']['replicas'] - node_pods[pod]
            config = copy.deepcopy(nodes[node_name]['pods'][pod])
            config['num_for_recreate'] = num_for_recreate
            config['total_num'] = nodes[node_name]['pods'][pod]['spec']['replicas']
            config['node'] = node_name
            broadcast_message('pods', config.__str__())
            del config
    for ReplicaSet in node_ReplicaSets:
        if node_ReplicaSets[ReplicaSet] < nodes[node_name]['ReplicaSets'][ReplicaSet]['spec']['replicas']:
            num_for_recreate = nodes[node_name]['ReplicaSets'][ReplicaSet]['spec']['replicas'] - node_ReplicaSets[ReplicaSet]
            config = copy.deepcopy(nodes[node_name]['ReplicaSets'][ReplicaSet])
            config['num_for_recreate'] = num_for_recreate
            config['total_num'] = nodes[node_name]['ReplicaSets'][ReplicaSet]['spec']['replicas']
            config['node'] = node_name
            broadcast_message('pods', config.__str__())
            del config
    print(nodes)
    print(pods)
    print(ReplicaSets)
    return json.dumps(heartbeat), 200



if __name__ == '__main__':
    if etcd.get('nodes')[0] is not None:
        nodes = ast.literal_eval(str(etcd.get('nodes')[0], 'UTF-8'))
        pods = ast.literal_eval(str(etcd.get('pods')[0], 'UTF-8'))
        ReplicaSets = ast.literal_eval(str(etcd.get('ReplicaSets')[0], 'UTF-8'))
    app.run(port=5050, processes=True)
