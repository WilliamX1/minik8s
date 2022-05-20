import re
import sys
import os
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
status = {'pods': {}, 'ReplicaSets': {}, 'cpu': 12, 'mem': total_memory}
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
    if config.get('num_for_recreate') is not None:
        # 恢复数量
        num_for_recreate = config['num_for_recreate']
        total_num = config['total_num']
        # 把对应的pod或ReplicaSet，cpu,mem修整一下，这个应该是pod自己检查发现并修改内存数据的，不是在这里+++++++++

        # 开启对应数量的
        if config['kind'] == 'pod':
            config = configs['pods'][config['name']]
            for i in range(0, num_for_recreate):
                suffix = create_suffix()
                configs['pods'][config['name']]['suffix'].append(suffix)
                re_config = copy.deepcopy(config)
                re_config['suffix'] = suffix
                status['pods'][re_config['name']] += 1
                status['mem'] -= entities.parse_bytes(re_config['mem'])
                status['cpu'] -= re_config['cpu']
                print("恢复数量")
                print("{} create pod {}{}".format(node_name, re_config['name'], re_config['suffix']))
                mem += entities.parse_bytes(re_config['mem'])
                set_cpu(re_config)
                pods[re_config['name']][re_config['suffix']] = entities.Pod(re_config, False)
                del re_config
        if config['kind'] == 'ReplicaSet':
            config = configs['ReplicaSet'][config['name']]
            for i in range(0, num_for_recreate):
                suffix = create_suffix()
                configs['ReplicaSet'][config['name']]['suffix'].append(suffix)
                re_config = copy.deepcopy(config)
                re_config['suffix'] = suffix
                status['ReplicaSet'][re_config['name']] += 1
                status['mem'] -= entities.parse_bytes(re_config['mem'])
                status['cpu'] -= re_config['cpu']
                mem += entities.parse_bytes(re_config['mem'])
                set_cpu(re_config)
                print("恢复数量")
                print("{} create ReplicaSet {}{}".format(node_name, re_config['name'], re_config['suffix']))
                ReplicaSets[re_config['name']][re_config['suffix']] = entities.Pod(re_config, False)
                del re_config
    else:
        # 新开或扩容
        if config['kind'] == 'pod':
            # pod只产生一个后缀
            config['suffix'] = []
            config['suffix'].append(create_suffix())
            re_config = copy.deepcopy(config)
            re_config['suffix'] = config['suffix'][0]
            # 更新configs
            configs['pods'][config['name']] = config
            print("创建")
            print("{} create pod {}{}".format(node_name, re_config['name'], re_config['suffix']))
            # 更新status
            status['pods'][config['name']] = 1
            status['mem'] -= entities.parse_bytes(re_config['mem'])
            status['cpu'] -= re_config['cpu']
            mem += entities.parse_bytes(re_config['mem'])
            set_cpu(re_config)
            # 创建pod并更新内存pods
            pods[re_config['name']] = {}
            pods[re_config['name']][re_config['suffix']] = entities.Pod(re_config, False)
            del re_config
        if config['kind'] == 'service':
            raise NotImplementedError
        if config['kind'] == 'ReplicaSet':
            # ReplicaSet产生多个后缀
            config['suffix'] = []
            replica_num = config['spec']['replicas']
            for i in range(0, replica_num):
                config['suffix'].append(create_suffix())
            # 更新内存configs
            configs['ReplicaSets'][config['name']] = config
            # 准备参数
            re_config = copy.deepcopy(config)
            ReplicaSets[re_config['name']] = {}
            # 更新status
            status['ReplicaSets'][config['name']] = replica_num
            for i in range(0, replica_num):
                re_config = copy.deepcopy(config)
                re_config['suffix'] = configs['ReplicaSets'][config['name']]['suffix'][i]
                status['mem'] -= entities.parse_bytes(re_config['mem'])
                status['cpu'] -= re_config['cpu']
                mem += entities.parse_bytes(re_config['mem'])
                set_cpu(re_config)
                print("创建")
                print("{} create ReplicaSet {}{}".format(node_name, re_config['name'], re_config['suffix']))
                # 创建ReplicaSet并更新内存ReplicaSets
                ReplicaSets[re_config['name']][re_config['suffix']] = entities.Pod(re_config, False)
                del re_config
        if config['kind'] == 'HorizontalPodAutoscaler':
            replica_num = config['config']['spec']['replicas']
            if config['prekind'] == 'pod':
                if not configs['pods'].__contains__(config['name']):
                    configs['pods'][config['name']] = config['config']
                    configs['pods'][config['name']]['suffix'] = []
                    config = configs['pods'][config['name']]
                    pods[config['name']] = {}
                else:
                    config = configs['pods'][config['name']]
                for i in range(0, replica_num):
                    suffix = create_suffix()
                    configs['pods'][config['name']]['suffix'].append(suffix)
                    re_config = copy.deepcopy(config)
                    re_config['suffix'] = suffix
                    status['pods'][re_config['name']] += 1
                    status['mem'] -= entities.parse_bytes(re_config['mem'])
                    status['cpu'] -= re_config['cpu']
                    mem += entities.parse_bytes(re_config['mem'])
                    set_cpu(re_config)
                    print("扩容")
                    print("{} create pod {}{}".format(node_name, re_config['name'], re_config['suffix']))
                    pods[re_config['name']][re_config['suffix']] = entities.Pod(re_config, False)
                    del re_config
            elif config['prekind'] == 'ReplicaSet':
                if not configs['ReplicaSets'].__contains__(config['name']):
                    configs['ReplicaSets'][config['name']] = config['config']
                    configs['ReplicaSets'][config['name']]['suffix'] = []
                    config = configs['ReplicaSets'][config['name']]
                    ReplicaSets[config['name']] = {}
                else:
                    config = configs['ReplicaSet'][config['name']]
                for i in range(0, replica_num):
                    suffix = create_suffix()
                    configs['ReplicaSet'][config['name']]['suffix'].append(suffix)
                    re_config = copy.deepcopy(config)
                    re_config['suffix'] = suffix
                    status['ReplicaSet'][re_config['name']] += 1
                    status['mem'] -= entities.parse_bytes(re_config['mem'])
                    status['cpu'] -= re_config['cpu']
                    print("扩容")
                    print("{} create ReplicaSet {}{}".format(node_name, re_config['name'], re_config['suffix']))
                    mem += entities.parse_bytes(re_config['mem'])
                    set_cpu(re_config)
                    ReplicaSets[re_config['name']][re_config['suffix']] = entities.Pod(re_config, False)
                    del re_config


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
