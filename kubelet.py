import re
import sys
import os
import time

import const
import utils
import yaml_loader
import entities
import string
import random
import pika
import ast
import requests
import json
import six
import copy
import memcache
import uuid
import psutil
import shutil

node_instance_name = uuid.uuid1().__str__()

pods = list()

api_server_url = const.api_server_url


def get_pod_by_name(instance_name: str):
    index = -1
    pod: entities.Pod = None
    for i in range(len(pods)):
        if pods[i].instance_name == instance_name:
            index = i
            pod = pods[i]
            break
    return index, pod


# 回调函数
def hand_pods(ch, method, properties, body):
    config: dict = ast.literal_eval(body.decode())

    print("get broadcast ", config)
    # config中不含node或者node不是自己都丢弃
    if not config.__contains__('node') or config['node'] != node_instance_name\
            or not config.__contains__('behavior'):
        return
    instance_name = config['instance_name']
    if config['behavior'] == 'create':
        print("接收到调度请求 Pod")
        # 是自己的调度，进行操作
        pods.append(entities.Pod(config))
        print('{} create pod {}'.format(node_instance_name, instance_name))
        # share.set('status', str(status))
    elif config['behavior'] == 'remove':
        print('try to delete Pod {}'.format(instance_name))
        index, pod = get_pod_by_name(instance_name)
        if index == -1:  # pod not found
            return
        pods.pop(index)
        pod.remove()
    elif config['behavior'] == 'execute':
        # todo: check the logic here
        print('try to execute Pod {} {}'.format(instance_name, config['cmd']))
        index, pod = get_pod_by_name(instance_name)
        print(pod)
        cmd = config['cmd']
        pod.exec_run(cmd)


def send_heart_beat():
    data = psutil.virtual_memory()
    total = data.total  # 总内存,单位为byte
    free = data.available  # 可用内存
    memory_use_percent = (int(round(data.percent)))
    cpu_use_percent = psutil.cpu_percent(interval=None)
    config: dict = {'instance_name': node_instance_name, 'kind': 'Node', 'total_memory': total,
                    'cpu_use_percent': cpu_use_percent, 'memory_use_percent': memory_use_percent,
                    'free_memory': free, 'status': 'RUNNING', 'pod_instances': list()}
    for pod in pods:
        pod_status_heartbeat = dict()
        pod_status = pod.get_status()
        pod_status_heartbeat['instance_name'] = pod.instance_name
        pod_status_heartbeat['status'] = pod_status['status']
        pod_status_heartbeat['cpu_usage_percent'] = pod_status['cpu_usage_percent']
        pod_status_heartbeat['memory_usage_percent'] = pod_status['memory_usage_percent']
        pod_status_heartbeat['ip'] = pod_status['ip']
        config['pod_instances'].append(pod.instance_name)
        config[pod.instance_name] = pod_status_heartbeat

    url = "{}/heartbeat".format(api_server_url)
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)
    if r.status_code == 200:
        print("发送心跳包成功")
        pass
    else:
        print("发送心跳包失败")
        exit()


def init_node():
    # delete original iptables and restore
    dir = const.dns_conf_path
    for f in os.listdir(dir):
        if f != 'default.conf':
            os.remove(os.path.join(dir, f))
    utils.exec_command(command="echo "" > /etc/hosts", shell=True)
    utils.exec_command(command="iptables-restore < ./sources/iptables", shell=True)
    # todo: add other logic here
    os.system('docker stop $(docker ps -a -q)')
    os.system('docker rm $(docker ps -a -q)')
    data = psutil.virtual_memory()
    total = data.total  # 总内存,单位为byte
    free = data.available  # 可用内存
    memory_use_percent = (int(round(data.percent)))
    cpu_use_percent = psutil.cpu_percent(interval=1)
    # print(data, total, free, memory, cpu_use_percent)
    config: dict = {'instance_name': node_instance_name, 'kind': 'Node', 'total_memory': total,
                    'cpu_use_percent': cpu_use_percent, 'memory_use_percent': memory_use_percent,
                    'free_memory': free}
    url = "{}/Node".format(api_server_url)
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)
    if r.status_code == 200:
        print("kubelet节点注册成功")
    else:
        print("kubelet节点注册失败")
        exit()


def main():
    init_node()
    # 创建socket链接,声明管道
    connect = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connect.channel()
    # 声明exchange名字和类型
    channel.exchange_declare(exchange="Pod", exchange_type="fanout")
    # rabbit会随机分配一个名字, exclusive=True会在使用此queue的消费者断开后,自动将queue删除，result是queue的对象实例
    result = channel.queue_declare(queue="")  # 参数 exclusive=True 独家唯一的
    queue_name = result.method.queue  # 绑定pods频道

    channel.queue_bind(exchange="Pod", queue=queue_name)
    # 消费信息
    channel.basic_consume(on_message_callback=hand_pods, queue=queue_name, auto_ack=True)
    # channel.basic_consume(on_message_callback=callback, queue=queue_name, auto_ack=True)
    # 开始消费
    # channel.start_consuming()
    # Check if called from the scope of an event dispatch callback
    with channel.connection._acquire_event_dispatch() as dispatch_allowed:
        if not dispatch_allowed:
            raise Exception(
                'start_consuming may not be called from the scope of '
                'another BlockingConnection or BlockingChannel callback')
    channel._impl._raise_if_not_open()
    # Process events as long as consumers exist on this channel
    while channel._consumer_infos:
        send_heart_beat()
        # This will raise ChannelClosed if channel is closed by broker
        channel._process_data_events(time_limit=5)


if __name__ == '__main__':
    main()
