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

node_name = 'node1'
per_cpu_size = 2.2 * 1024 * 1024 * 1024
cpu_sum = 12
total_memory = 5 * 1024 * 1024 * 1024
configs = {'pods': {}, 'ReplicaSets': {}}
#         'pods':{podname:config},              //  config的'suffix'是所有后缀的数组
#         'ReplicaSets':{ReplicaSetname:config} //  config的'suffix'是所有后缀的数组
pods = {}
#       podname:{suffix:pod}
ReplicaSets = {}
#       ReplicaSetname:{suffix:ReplicaSet}
cpu = {'0': 0, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '7': 0, '8': 0, '9': 0, '10': 0, '11': 0}  # 0代表未被占用
mem = 0
# status方便发送心跳包
status = {'pods': {}, 'ReplicaSets': {}, 'cpu': cpu_sum, 'mem': total_memory}
#         'pods':{podname:replicas},
#         'ReplicaSets':{ReplicaSetname:replicas},
#         'cpu',             //这里的mem和cpu都是定义可用数
#         'mem'

# 与发送心跳脚本共享node信息
share = memcache.Client(["127.0.0.1:11211"], debug=True)
share.set('status', str(status))


# 指派cpu并更新cpu
def set_cpu(re_config):
    containers = re_config['containers']
    for container in containers:
        cpugroup = ''
        cpu_num = container['resource']['cpu']
        while cpu_num > 0:
            for cpuid in cpu:
                if cpu[cpuid] == 0:
                    cpugroup += ',' + cpuid
                    cpu[cpuid] = 1
                    cpu_num -= 1
                    if cpu_num == 0:
                        break
        cpugroup = re.sub(r'.', '', cpugroup, count=1)
        container['resource']['cpu'] = cpugroup


# 创建后缀
def create_suffix():
    res = ''.join(random.choices(string.ascii_letters +
                                 string.digits, k=10))
    res = '-' + res
    return res


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

def cpu_set(config, container_cpu):
    for container in config['containers']:
        container['resource']['cpu'] = container_cpu[container['name']]


# 回调函数
def callback(ch, method, properties, body):
    global mem
    config: dict = ast.literal_eval(body.decode())
    # config中不含node或者node不是自己都丢弃
    if not config.__contains__('node'):
        return
    if config['node'] != node_name:
        return
    # 是自己的调度，进行操作
    if config['kind'] == 'pod':
        if configs['pods'].__contains__(config['name']):
            config['suffix'] = configs['pods'][config['name']]['suffix']
            status['pods'][config['name']] += config['spec']['replicas']
        else:
            config['suffix'] = []
            status['pods'][config['name']] = config['spec']['replicas']
        status['mem'] -= entities.parse_bytes(config['mem']) * config['spec']['replicas']
        status['cpu'] -= config['cpu'] * config['spec']['replicas']
        mem += entities.parse_bytes(config['mem']) * config['spec']['replicas']
        for i in range(0, config['spec']['replicas']):
            suffix = create_suffix()
            config['suffix'].append(suffix)
            re_config = copy.deepcopy(config)
            re_config['suffix'] = suffix
            set_cpu(re_config)
            if not pods.__contains__(re_config['name']):
                pods[re_config['name']] = {}
            print('{} create pod {}{}'.format(node_name, re_config['name'], re_config['suffix']))
            pods[re_config['name']][re_config['suffix']] = entities.Pod(re_config, False)
        configs['pods'][config['name']] = config
    if config['kind'] == 'service':
        raise NotImplementedError
    if config['kind'] == 'ReplicaSet':
        if configs['ReplicaSets'].__contains__(config['name']):
            config['suffix'] = configs['ReplicaSets'][config['name']]['suffix']
            status['ReplicaSets'][config['name']] += config['spec']['replicas']
        else:
            config['suffix'] = []
            status['ReplicaSets'][config['name']] = config['spec']['replicas']
        status['mem'] -= entities.parse_bytes(config['mem']) * config['spec']['replicas']
        status['cpu'] -= config['cpu'] * config['spec']['replicas']
        mem += entities.parse_bytes(config['mem']) * config['spec']['replicas']
        for i in range(0, config['spec']['replicas']):
            suffix = create_suffix()
            config['suffix'].append(suffix)
            re_config = copy.deepcopy(config)
            re_config['suffix'] = suffix
            set_cpu(re_config)
            if not ReplicaSets.__contains__(re_config['name']):
                ReplicaSets[re_config['name']] = {}
            print('{} create ReplicaSet {}{}'.format(node_name, re_config['name'], re_config['suffix']))
            ReplicaSets[re_config['name']][re_config['suffix']] = entities.Pod(re_config, False)
        configs['ReplicaSets'][config['name']] = config
    if config['kind'] == 'delete':
        if config['target_kind'] == 'pod':
            status['cpu'] += configs['pods'][config['target_name']]['cpu'] * config['num']
            status['mem'] += entities.parse_bytes(configs['pods'][config['target_name']]['mem']) * config['num']
            status['pods'][config['target_name']] -= config['num']
            mem -= entities.parse_bytes(configs['pods'][config['target_name']]['mem']) * config['num']
            for i in range(0, config['num']):
                cpu_list = pods[config['target_name']][configs['pods'][config['target_name']]['suffix'][0]].cpu()
                for c in cpu_list:
                    cpu[c] = 0
                pods[config['target_name']][configs['pods'][config['target_name']]['suffix'][0]].remove()
                print('{} delete pod {}{}'.format(node_name, config['target_name'],
                                                  configs['pods'][config['target_name']]['suffix'][0]))
                del pods[config['target_name']][configs['pods'][config['target_name']]['suffix'][0]]
                del configs['pods'][config['target_name']]['suffix'][0]
            if len(configs['pods'][config['target_name']]['suffix']) == 0:
                del pods[config['target_name']]
                del configs['pods'][config['target_name']]
                del status['pods'][config['target_name']]
        if config['target_kind'] == 'ReplicaSet':
            status['cpu'] += configs['ReplicaSets'][config['target_name']]['cpu'] * config['num']
            status['mem'] += entities.parse_bytes(configs['ReplicaSets'][config['target_name']]['mem']) * config['num']
            status['ReplicaSets'][config['target_name']] -= config['num']
            mem -= entities.parse_bytes(configs['ReplicaSets'][config['target_name']]['mem']) * config['num']
            for i in range(0, config['num']):
                print(ReplicaSets)
                cpu_list = ReplicaSets[config['target_name']][
                    configs['ReplicaSets'][config['target_name']]['suffix'][0]].cpu()
                for c in cpu_list:
                    cpu[c] = 0
                ReplicaSets[config['target_name']][configs['ReplicaSets'][config['target_name']]['suffix'][0]].remove()
                print('{} delete ReplicaSet {}{}'.format(node_name, config['target_name'],
                                                         configs['ReplicaSets'][config['target_name']]['suffix'][0]))
                del ReplicaSets[config['target_name']][configs['ReplicaSets'][config['target_name']]['suffix'][0]]
                del configs['ReplicaSets'][config['target_name']]['suffix'][0]
            if len(configs['ReplicaSets'][config['target_name']]['suffix']) == 0:
                del ReplicaSets[config['target_name']]
                del configs['ReplicaSets'][config['target_name']]
                del status['ReplicaSets'][config['target_name']]
    if config['kind'] == 'HorizontalPodAutoscaler':
        config = config['config']
        num = config['num']
        # 存储现存的该pod或replicaset的每个副本的资源使用情况
        resource_status_list = {}
        if config['kind'] == 'pod':
            for pod in pods[config['name']]:
                resource_status_list[pod] = pods[config['name']][pod].resource_status()
                # 释放原cpu和mem，设定新的cpu和内存
                cpu_list = pods[config['name']][pod].cpu()
                pre_mem = entities.parse_bytes(pods[config['name']][pod].mem())
                for c in cpu_list:
                    cpu[c] = 0
                re_config = copy.deepcopy(config)
                set_cpu(re_config)
                mem -= pre_mem - entities.parse_bytes(re_config['mem'])
                status['cpu'] += len(cpu_list) - re_config['cpu']
                status['mem'] += pre_mem - entities.parse_bytes(re_config['mem'])
                # 修改原pod的容器资源使用情况
                pods[config['name']][pod].rescale(re_config)
            config['suffix'] = configs['pods'][config['name']]['suffix']
        if config['kind'] == 'ReplicaSet':
            for ReplicaSet in ReplicaSets[config['name']]:
                resource_status_list[ReplicaSet] = ReplicaSets[config['name']][ReplicaSet].resource_status()
                # 释放原cpu和mem，设定新的cpu和内存
                cpu_list = ReplicaSets[config['name']][ReplicaSet].cpu()
                pre_mem = entities.parse_bytes(ReplicaSets[config['name']][ReplicaSet].mem())
                for c in cpu_list:
                    cpu[c] = 0
                re_config = copy.deepcopy(config)
                set_cpu(re_config)
                mem -= pre_mem - entities.parse_bytes(config['mem'])
                status['cpu'] += len(cpu_list) - config['cpu']
                status['mem'] += pre_mem - entities.parse_bytes(config['mem'])
                # 修改原ReplicaSet的容器资源使用情况
                ReplicaSets[config['name']][ReplicaSet].rescale(re_config)
            config['suffix'] = configs['ReplicaSets'][config['name']]['suffix']
        for resource_status in resource_status_list:
            # auto_num是以该pod为基础能扩容多少个副本
            # num是给该node分配的配额
            auto_num = 0
            while (auto_num + 1) * resource_status_list[resource_status]['mem'] < 1 and (auto_num + 1) * resource_status_list[resource_status]['cpu'] < 1:
                auto_num += 1
                num -= 1
                if num == 0:
                    break
            re_config = copy.deepcopy(config)
            if config['kind'] == 'pod':
                # 将re_config的containers的cpu情况改成和pods[re_config['name']][resource_status]一样
                for i in range(0, auto_num):
                    suffix = create_suffix()
                    config['suffix'].append(suffix)
                    re_config['suffix'] = suffix
                    cpu_set(re_config, pods[re_config['name']][resource_status].container_cpu())
                    print('rescale pod {}{}'.format(re_config['name'], suffix))
                    pods[config['name']][suffix] = entities.Pod(re_config, False)
                    # 向api_server发送扩容消息
                    msg = {'node': node_name, 'kind': 'pod', 'name': re_config['name']}
                    url = "http://127.0.0.1:5050/rescale"
                    json_data = json.dumps(msg)
                    r = requests.post(url=url, json=json_data)
                    time.sleep(2)
            if config['kind'] == 'ReplicaSet':
                # 将re_config的containers的cpu情况改成和ReplicaSets[re_config['name']][resource_status]一样
                for i in range(0, auto_num):
                    suffix = create_suffix()
                    config['suffix'].append(suffix)
                    re_config['suffix'] = suffix
                    cpu_set(re_config, ReplicaSets[re_config['name']][resource_status].container_cpu())
                    print('rescale ReplicaSet {}{}'.format(re_config['name'], suffix))
                    ReplicaSets[config['name']][suffix] = entities.Pod(re_config, False)
                    # 向api_server发送扩容消息
                    msg = {'node': node_name, 'kind': 'ReplicaSet', 'name': re_config['name']}
                    url = "http://127.0.0.1:5050/rescale"
                    json_data = json.dumps(msg)
                    r = requests.post(url=url, json=json_data)
                    time.sleep(2)
            if num == 0:
                break
        if config['kind'] == 'pod':
            configs['pods'][config['name']] = config
        if config['kind'] == 'ReplicaSet':
            configs['ReplicaSets'][config['name']] = config
    share.set('status', str(status))


def main():
    # 创建socket链接,声明管道
    connect = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connect.channel()
    # 声明exchange名字和类型
    channel.exchange_declare(exchange="pods", exchange_type="fanout")
    # rabbit会随机分配一个名字, exclusive=True会在使用此queue的消费者断开后,自动将queue删除，result是queue的对象实例
    result = channel.queue_declare(queue="", exclusive=True)  # 参数 exclusive=True 独家唯一的
    queue_name = result.method.queue
    # 绑定pods频道
    channel.queue_bind(exchange="pods", queue=queue_name)
    # 消费信息
    channel.basic_consume(on_message_callback=callback, queue=queue_name, auto_ack=True)
    # 开始消费
    channel.start_consuming()


if __name__ == '__main__':
    main()
