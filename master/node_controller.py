import json
import os
import sys
import time

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
import const, yaml_loader

ROOT_DIR = os.path.join(BASE_DIR, os.path.pardir)
yaml_path = os.path.join(ROOT_DIR, 'worker', 'nodes_yaml', 'master.yaml')
etcd_info_config: dict = yaml_loader.load(yaml_path)
api_server_url = etcd_info_config['API_SERVER_URL']


def main():
    while True:
        time.sleep(1)
        nodes_dict = None
        try:
            r = requests.get(url='{}/Node'.format(api_server_url))
            nodes_dict = json.loads(r.content.decode('UTF-8'))
            valid_nodes_list = list()
            current_sec = time.time()
            for node_instance_name in nodes_dict['nodes_list']:
                current_node = nodes_dict[node_instance_name]
                if current_node['status'] == 'Not Available':
                    continue
                valid_nodes_list.append(node_instance_name)
                last_receive_time = current_node['last_receive_time']
                # print(current_sec, last_receive_time)
                if current_sec - last_receive_time > 200:
                    print("Node {} timeout!".format(node_instance_name))
                    r = requests.delete(url='{}/Node/{}'.format(api_server_url, node_instance_name))
            print("当前注册的Node为：{}".format(valid_nodes_list))
        except Exception as e:
            print('Connect API Server Failure!', e)
            continue


if __name__ == '__main__':
    main()
