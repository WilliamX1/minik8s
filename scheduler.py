import pika
import ast
import requests
import json
import six
import sys
from entities import parse_bytes

total_memory = 5 * 1024 * 1024 * 1024


# 回调函数
# 暂时认为调度都能成功
def callback(ch, method, properties, body):
    # 对请求进行调度，nodes信息储存在config['nodes']中
    config: dict = ast.literal_eval(body.decode())
    instance_name = config['instance_name']
    if config['kind'] == 'pod':
        if not config.__contains__('node'):
            if config.__contains__('reschedule'):
                print("scheduler receive reschedule pod config")
                reschedule_num = config['reschedule']
                del config['reschedule']
                mem_need = parse_bytes(config['mem'])
                while reschedule_num > 0:
                    for node in config['nodes']:
                        if config['nodes'][node]['cpu'] >= config['cpu'] and config['nodes'][node]['mem'] >= mem_need:
                            config['nodes'][node]['cpu'] -= config['cpu']
                            config['nodes'][node]['mem'] -= mem_need
                            reschedule_num -= 1
                            config['node'] = node
                            break
                        print('reschedule one pod replica {} to {}'.format(config['name'], config['node']))
                        url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
                        json_data = json.dumps(config)
                        # 向api_server发送调度结果
                        r = requests.post(url=url, json=json_data)
            else:
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
    # +++++++++++++++++
    if config['kind'] == 'HorizontalPodAutoscaler':
        if not config.__contains__('node'):
            print("scheduler receive HorizontalPodAutoscaler config")
            minReplicas = config['minReplicas']
            maxReplicas = config['maxReplicas']
            targetReplicas = (minReplicas + maxReplicas) / 2
            if targetReplicas <= config['config']['spec']['replicas']:
                return
            replica_num = targetReplicas - config['config']['spec']['replicas']
            mem_need = parse_bytes(config['config']['mem'])
            for node in config['nodes']:
                config['nodes'][node]['replicas'] = 0
            while replica_num > 0:
                for node in config['nodes']:
                    if config['nodes'][node]['cpu'] >= config['config']['cpu'] and config['nodes'][node]['mem'] >= mem_need:
                        config['nodes'][node]['cpu'] -= config['config']['cpu']
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
                    config['config']['spec']['replicas'] = config['nodes'][node]['replicas']
                    url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
                    json_data = json.dumps(config)
                    print('send replicanum {} to {}'.format(config['config']['spec']['replicas'], node))
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
