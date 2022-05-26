import copy
import time

import pika
import ast
import requests
import json
import six
import sys

import const
from entities import parse_bytes

api_server_url = const.api_server_url


# 回调函数
def callback(ch, method, properties, body):
    config: dict = ast.literal_eval(body.decode())
    if config['kind'] == 'Pod' and config['status'] == 'Wait for Schedule':
        r = requests.get(url='{}/Node'.format(api_server_url))
        nodes_dict = json.loads(r.content.decode('UTF-8'))
        instance_name = config['instance_name']
        mem_need = parse_bytes(config['mem'])
        config['status'] = 'Schedule Failed'
        if len(nodes_dict['nodes_list']) == 0:
            print("no node registered !")
        for node_instance_name in nodes_dict['nodes_list']:
            current_node = nodes_dict[node_instance_name]
            print("free_memory = {}, need_memory = {}".format(current_node['free_memory'], mem_need))
            if current_node['free_memory'] > mem_need:
                config['node'] = node_instance_name
                config['status'] = 'Ready to Create'
                break
        if config.__contains__('node'):
            print('把 pod {} 调度到节点 {} 上'.format(instance_name, config['node']))
        else:
            print("Schedule failure")
        url = "{}/Pod/{}/create".format(api_server_url, instance_name)
        json_data = json.dumps(config)
        # 向api_server发送调度结果
        r = requests.post(url=url, json=json_data)


def main():
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
    channel.basic_consume(on_message_callback=callback, queue=queue_name, auto_ack=True)
    # 开始消费
    channel.start_consuming()


if __name__ == '__main__':
    main()
