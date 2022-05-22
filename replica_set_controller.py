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


# def callback(ch, method, properties, body):
#     replica_set_config: dict = ast.literal_eval(body.decode())
#     expected_replica_number = replica_set_config['spec']['replicas']
#     current_replica_number = replica_set_config['current_instance_number']
#     pod_config = copy.deepcopy(replica_set_config)
#     pod_config['kind'] = 'Pod'
#     pod_config.pop('spec')
#     print("Find a replica set")
#     while replica_set_config['current_instance_number'] < expected_replica_number:
#         url = api_server_url + 'Pod'
#         json_data = json.dumps(pod_config)
#         # 向api_server发送调度结果
#         r = requests.post(url=url, json=json_data)
#         pod_instance_name = json.loads(r.content.decode('UTF-8'))['instance_name']
#         print("pod_instance_name = {}".format(pod_instance_name))
#         replica_set_config['current_instance_number'] += 1
#         replica_set_config['pod_instances'].append(pod_instance_name)
#
#     url = "http://127.0.0.1:5050/ReplicaSet/{}".format(replica_set_config['instance_name'])
#     json_data = json.dumps(replica_set_config)
#     # 向api_server发送调度结果
#     r = requests.post(url=url, json=json_data)


if __name__ == '__main__':
    while True:
        try:
            r = requests.get(url=api_server_url + 'ReplicaSet')
            replica_set_dict = json.loads(r.content.decode('UTF-8'))
        except Exception as e:
            print('Connect API Server Failure!')
            continue
        print("当前的ReplicaSet为：{}".format(replica_set_dict['replica_sets_list']))
        current_sec = time.time()
        for replica_set_name in replica_set_dict['replica_sets_list']:
            replica_config = replica_set_dict[replica_set_name]

            # print("config = ", replica_config['pod_instances'])
            expected_replica_number = replica_config['spec']['replicas']
            current_replica_number = 0
            remove_index = list()
            for index, pod_instance_name in enumerate(replica_config['pod_instances']):
                pod_instance_config = replica_set_dict[pod_instance_name]
                # todo : check the status of the pod
                if pod_instance_config.__contains__('node') and pod_instance_config['node'] != 'NOT AVAILABLE':
                    current_replica_number += 1
                else:
                    remove_index.append(index)
            remove_index.reverse()
            for index in remove_index:
                replica_config['pod_instances'].pop(index)
            print("Replica Set need create {} new instances".format(str(expected_replica_number - current_replica_number)))
            while current_replica_number < expected_replica_number:
                pod_config = copy.deepcopy(replica_config)
                pod_config['kind'] = 'Pod'
                pod_config.pop('spec')
                pod_config.pop('pod_instances')
                json_data = json.dumps(pod_config)
                r = requests.post(url=api_server_url + 'Pod', json=json_data)
                pod_instance_name = json.loads(r.content.decode('UTF-8'))['instance_name']
                print("pod_instance_name = {}".format(pod_instance_name))
                replica_config['pod_instances'].append(pod_instance_name)
                current_replica_number += 1
            url = "http://127.0.0.1:5050/ReplicaSet/{}".format(replica_config['instance_name'])
            json_data = json.dumps(replica_config)
            r = requests.post(url=url, json=json_data)

        time.sleep(1)

