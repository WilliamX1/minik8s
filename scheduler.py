import copy
import time

import pika
import ast
import requests
import json
import six
import sys
from entities import parse_bytes


# 回调函数
# 暂时认为调度都能成功
def callback(ch, method, properties, body):
    # 对请求进行调度，nodes信息储存在config['nodes']中
    config: dict = ast.literal_eval(body.decode())
    if config['kind'] == 'pod':
        if not config.__contains__('node'):
            instance_name = config['instance_name']
            print("scheduler receive pod config")
            mem_need = parse_bytes(config['mem'])
            for node in config['nodes']:
                if config['nodes'][node]['cpu'] >= config['cpu'] and config['nodes'][node]['mem'] >= mem_need:
                    config['node'] = node
                    break
            print('schedule pod {} to {}'.format(config['name'], config['node']))
            url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
            json_data = json.dumps(config)
            # 向api_server发送调度结果
            r = requests.post(url=url, json=json_data)
    if config['kind'] == 'ReplicaSet':
        if not config.__contains__('node'):
            instance_name = config['instance_name']
            print("scheduler receive ReplicaSet config")
            replica_num = config['spec']['replicas']
            mem_need = parse_bytes(config['mem'])
            for node in config['nodes']:
                config['nodes'][node]['replicas'] = 0
            while replica_num > 0:
                for node in config['nodes']:
                    if config['nodes'][node]['cpu'] >= config['cpu'] and config['nodes'][node]['mem'] >= mem_need:
                        config['nodes'][node]['cpu'] -= config['cpu']
                        config['nodes'][node]['mem'] -= mem_need
                        config['nodes'][node]['replicas'] += 1
                        print('schedule one replica to {}'.format(node))
                        replica_num -= 1
                        if replica_num == 0:
                            break
            print('schedule result as below:')
            for node in config['nodes']:
                if config['nodes'][node]['replicas'] > 0:
                    config['node'] = node
                    config['spec']['replicas'] = config['nodes'][node]['replicas']
                    url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
                    json_data = json.dumps(config)
                    print('send replicanum {} to {}'.format(config['spec']['replicas'], node))
                    # 向api_server发送调度结果
                    r = requests.post(url=url, json=json_data)
    if config['kind'] == 'reschedule':
        pods_for_restart = config['pods']
        ReplicaSets_for_restart = config['ReplicaSets']
        nodes = config['nodes']
        configs = copy.deepcopy(pods_for_restart)
        configs.update(ReplicaSets_for_restart)
        for config_name in configs:
            config = configs[config_name]
            instance_name = config['instance_name']
            replica_num = config['spec']['replicas']
            mem_need = parse_bytes(config['mem'])
            for node in nodes:
                nodes[node]['replicas'] = 0
            while replica_num > 0:
                for node in nodes:
                    if nodes[node]['cpu'] >= config['cpu'] and nodes[node]['mem'] >= mem_need:
                        nodes[node]['cpu'] -= config['cpu']
                        nodes[node]['mem'] -= mem_need
                        nodes[node]['replicas'] += 1
                        print('reschedule one replica to {}'.format(node))
                        replica_num -= 1
                        if replica_num == 0:
                            break
            print('{} {} reschedule result as below:'.format(config['kind'], config['name']))
            for node in nodes:
                if nodes[node]['replicas'] > 0:
                    config['node'] = node
                    config['spec']['replicas'] = config['nodes'][node]['replicas']
                    url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
                    json_data = json.dumps(config)
                    print('send replicanum {} to {}'.format(config['spec']['replicas'], node))
                    # 向api_server发送调度结果
                    r = requests.post(url=url, json=json_data)
    if config['kind'] == 'HorizontalPodAutoscaler':
        if not config.__contains__('node'):
            print("scheduler receive HorizontalPodAutoscaler config")
            instance_name = config['instance_name']
            minReplicas = config['minReplicas']
            maxReplicas = config['maxReplicas']
            nodes = config['nodes']
            config = config['config']
            mem_need = parse_bytes(config['mem'])
            if config['spec']['replicas'] > minReplicas:
                # 做schedule并删除至minReplicas，修改nodes情况
                num_for_delete = config['spec']['replicas'] - minReplicas
                kind = config['kind']
                group = kind + 's'
                for node in nodes:
                    nodes[node]['replicas'] = 0
                while num_for_delete > 0:
                    for node in nodes:
                        if nodes[node][group].__contains__(config['name']):
                            nodes[node][group][config['name']]['spec']['replicas'] -= 1
                            if nodes[node][group][config['name']]['spec']['replicas'] == 0:
                                del nodes[node][group][config['name']]
                            nodes[node]['cpu'] += config['cpu']
                            nodes[node]['mem'] += mem_need
                            nodes[node]['replicas'] += 1
                            num_for_delete -= 1
                            if num_for_delete == 0:
                                break
                for node in nodes:
                    if nodes[node]['replicas'] > 0:
                        print('schedule {} delete {} {} for {}'.format(node, kind, config['name'],
                                                                       nodes[node]['replicas']))
                        msg = {'node': node, 'kind': 'delete', 'target_name': config['name'], 'target_kind': kind,
                               'num': nodes[node]['replicas']}
                        url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
                        json_data = json.dumps(msg)
                        # 向api_server发送调度结果
                        r = requests.post(url=url, json=json_data)
            if config['spec']['replicas'] < minReplicas:
                # 做schedule并增加至minReplicas，修改nodes情况
                num_for_create = minReplicas - config['spec']['replicas']
                re_config = copy.deepcopy(config)
                for node in nodes:
                    nodes[node]['replicas'] = 0
                while num_for_create > 0:
                    for node in nodes:
                        if nodes[node]['cpu'] >= re_config['cpu'] and nodes[node]['mem'] >= mem_need:
                            nodes[node]['cpu'] -= re_config['cpu']
                            nodes[node]['mem'] -= mem_need
                            nodes[node]['replicas'] += 1
                            print('reschedule one replica to {}'.format(node))
                            num_for_create -= 1
                            if num_for_create == 0:
                                break
                print('schedule result as below:')
                for node in nodes:
                    if nodes[node]['replicas'] > 0:
                        re_config['node'] = node
                        re_config['spec']['replicas'] = nodes[node]['replicas']
                        if re_config['kind'] == 'pod':
                            if nodes[node]['pods'].__contains__(re_config['name']):
                                nodes[node]['pods'][re_config['name']]['spec']['replicas'] += re_config['spec'][
                                    'replicas']
                            else:
                                nodes[node]['pods'][re_config['name']] = re_config
                        if re_config['kind'] == 'ReplicaSet':
                            if nodes[node]['ReplicaSets'].__contains__(re_config['name']):
                                nodes[node]['ReplicaSets'][re_config['name']]['spec']['replicas'] += re_config['spec'][
                                    'replicas']
                            else:
                                nodes[node]['ReplicaSets'][re_config['name']] = re_config
                        print('send replicanum {} to {}'.format(re_config['spec']['replicas'], node))
                        url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
                        json_data = json.dumps(re_config)
                        # 向api_server发送调度结果
                        r = requests.post(url=url, json=json_data)
            config['spec']['replicas'] = minReplicas
            time.sleep(10)
            for node in nodes:
                nodes[node]['num'] = 0
            scale_sum = maxReplicas - minReplicas
            print('scale num is {}'.format(scale_sum))
            while scale_sum > 0:
                for node in nodes:
                    if config['kind'] == 'pod':
                        if nodes[node]['pods'].__contains__(config['name']):
                            nodes[node]['num'] += 1
                            scale_sum -= 1
                    if config['kind'] == 'ReplicaSet':
                        if nodes[node]['ReplicaSets'].__contains__(config['name']):
                            nodes[node]['num'] += 1
                            scale_sum -= 1
                    if scale_sum == 0:
                        break
            for node in nodes:
                if nodes[node]['num'] > 0:
                    config['node'] = node
                    config['num'] = nodes[node]['num']
                    msg = {'kind': 'HorizontalPodAutoscaler', 'config': config}
                    url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
                    json_data = json.dumps(msg)
                    print('send scalenum {} to {}'.format(config['num'], node))
                    # 向api_server发送调度结果
                    r = requests.post(url=url, json=json_data)


if __name__ == '__main__':
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
