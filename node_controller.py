import copy
import time

import pika
import ast
import requests
import json
import six
import sys
from entities import parse_bytes

api_server_url = 'http://localhost:5050/'


if __name__ == '__main__':
    while True:
        time.sleep(1)
        nodes_dict = None
        try:
            r = requests.get(url=api_server_url + 'Node')
            nodes_dict = json.loads(r.content.decode('UTF-8'))
        except Exception as e:
            print('Connect API Server Failure!')
            continue
        print("当前注册的Node为：{}".format(nodes_dict['nodes_list']))
        current_sec = time.time()
        for node_instance_name in nodes_dict['nodes_list']:
            current_node = nodes_dict[node_instance_name]
            last_receive_time = current_node['last_receive_time']
            if current_sec - last_receive_time > 20:
                print("Node {} timeout!".format(node_instance_name))
                try:
                    r = requests.delete(url=api_server_url + 'Node/{}'.format(node_instance_name))
                except Exception as e:
                    print('Connect API Server Failure!')