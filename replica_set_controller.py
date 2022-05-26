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


# def callback(ch, method, properties, body):
#     replica_set_config: dict = ast.literal_eval(body.decode())
#     expected_replica_number = replica_set_config['spec']['replicas']
#     current_replica_number = replica_set_config['current_instance_number']
#     pod_config = copy.deepcopy(replica_set_config)
#     pod_config['kind'] = 'Pod'
#     pod_config.pop('spec')
#     print("Find a replica set")
#     while replica_set_config['current_instance_number'] < expected_replica_number:
#         url = '{}/Pod'.format(api_server_url)
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
def main():
    while True:
        try:
            r = requests.get(url='{}/ReplicaSet'.format(api_server_url))
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
            alive_pod_instances = list()
            for index, pod_instance_name in enumerate(replica_config['pod_instances']):
                if replica_set_dict.__contains__(pod_instance_name):
                    pod_instance_config = replica_set_dict[pod_instance_name]
                    # todo : check the status of the pod
                    pod_status = pod_instance_config['status']
                    if pod_status == 'Wait for Schedule' or pod_status == 'Ready to Create' or pod_status == 'Running':
                        alive_pod_instances.append(pod_instance_name)
            replica_config['pod_instances'] = alive_pod_instances
            print("Replica Set need create {} new instances".format(
                str(expected_replica_number - len(alive_pod_instances))))
            while len(replica_config['pod_instances']) < expected_replica_number:
                pod_config = copy.deepcopy(replica_config)
                pod_config['kind'] = 'Pod'
                pod_config.pop('spec')
                pod_config.pop('pod_instances')
                json_data = json.dumps(pod_config)
                r = requests.post(url='{}/Pod'.format(api_server_url), json=json_data)
                pod_instance_name = json.loads(r.content.decode('UTF-8'))['instance_name']
                print("pod_instance_name = {}".format(pod_instance_name))
                replica_config['pod_instances'].append(pod_instance_name)
            url = "{}/ReplicaSet/{}".format(api_server_url, replica_config['instance_name'])
            json_data = json.dumps(replica_config)
            r = requests.post(url=url, json=json_data)

        time.sleep(1)


if __name__ == '__main__':
    main()
