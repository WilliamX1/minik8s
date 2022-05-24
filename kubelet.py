import re
import sys
import os
import time

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

node_instance_name = uuid.uuid1().__str__()

pods = list()


# 回调函数
def hand_pods(ch, method, properties, body):
    config: dict = ast.literal_eval(body.decode())
    # config中不含node或者node不是自己都丢弃
    if not config.__contains__('node') or config['node'] != node_instance_name:
        return
    if config['status'] == 'Ready to Create':
        print("接收到调度请求 Pod")
        # 是自己的调度，进行操作
        pods.append(entities.Pod(config))
        print('{} create pod {}'.format(node_instance_name, config['instance_name']))
        # share.set('status', str(status))


def send_heart_beat():
    data = psutil.virtual_memory()
    total = data.total  # 总内存,单位为byte
    free = data.available  # 可用内存
    memory_use_percent = (int(round(data.percent)))
    cpu_use_percent = psutil.cpu_percent(interval=None)
    config: dict = {'instance_name': node_instance_name, 'kind': 'Node', 'total_memory': total, 'cpu_use_percent': cpu_use_percent, 'memory_use_percent': memory_use_percent,
                    'free_memory': free, 'status': 'RUNNING', 'pod_instances': list()}
    for pod in pods:
        pod_status_heartbeat = dict()
        pod_status = pod.get_status()
        print("POD_STATUS")
        pod_status_heartbeat['instance_name'] = pod.instance_name
        pod_status_heartbeat['status'] = pod_status['status']
        pod_status_heartbeat['cpu_usage_percent'] = pod_status['cpu_usage_percent']
        pod_status_heartbeat['memory_usage_percent'] = pod_status['memory_usage_percent']
        pod_status_heartbeat['ip'] = pod_status['ip']
        config['pod_instances'].append(pod.instance_name)
        config[pod.instance_name] = pod_status_heartbeat

    url = "http://127.0.0.1:5050/heartbeat"
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)
    if r.status_code == 200:
        print("发送心跳包成功")
        pass
    else:
        print("发送心跳包失败")
        exit()


def main():
    os.system('docker stop $(docker ps -a -q)')
    os.system('docker rm $(docker ps -a -q)')

    data = psutil.virtual_memory()
    total = data.total  # 总内存,单位为byte
    free = data.available  # 可用内存
    memory_use_percent = (int(round(data.percent)))
    cpu_use_percent = psutil.cpu_percent(interval=1)
    # print(data, total, free, memory, cpu_use_percent)
    config: dict = {'instance_name': node_instance_name, 'kind': 'Node', 'total_memory': total, 'cpu_use_percent': cpu_use_percent, 'memory_use_percent': memory_use_percent,
                    'free_memory': free}
    url = "http://127.0.0.1:5050/Node"
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)
    if r.status_code == 200:
        print("kubelet节点注册成功")
    else:
        print("kubelet节点注册失败")
        exit()

    # 创建socket链接,声明管道
    connect = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connect.channel()
    # 声明exchange名字和类型
    channel.exchange_declare(exchange="Pod", exchange_type="fanout")
    # rabbit会随机分配一个名字, exclusive=True会在使用此queue的消费者断开后,自动将queue删除，result是queue的对象实例
    result = channel.queue_declare(queue="")  # 参数 exclusive=True 独家唯一的
    queue_name = result.method.queue
    # 绑定pods频道
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
