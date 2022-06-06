import copy
import time

import requests
import json

import sys, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
import utils, const, yaml_loader


ROOT_DIR = os.path.join(BASE_DIR, os.path.pardir)
yaml_path = os.path.join(ROOT_DIR, 'worker', 'nodes_yaml', 'master.yaml')
etcd_info_config: dict = yaml_loader.load(yaml_path)
api_server_url = etcd_info_config['API_SERVER_URL']


def main():
    while True:
        time.sleep(3)
        try:
        # get replica set and pod information
            r = requests.get(url='{}/ReplicaSet'.format(api_server_url))
            replica_set_dict = json.loads(r.content.decode('UTF-8'))
            r = requests.get(url='{}/Pod'.format(api_server_url))
            pods_dict = json.loads(r.content.decode('UTF-8'))
            pods_list = pods_dict['pods_list']
            replica_sets_list = replica_set_dict['replica_sets_list']
            # check the replica set one by one
            for replica_set_name in replica_sets_list:
                replica_config = replica_set_dict[replica_set_name]
                alive_pod_instances = list()
                for pod_instance_name in pods_list:
                    if pods_dict.__contains__(pod_instance_name):
                        pod_instance_config = pods_dict[pod_instance_name]
                        pod_status = pod_instance_config.get('status')
                        if pod_instance_config.get('belong_to') == replica_set_name:
                            if pod_status == 'Wait for Schedule' or pod_status == 'Ready to Create' or pod_status == 'Running':
                                alive_pod_instances.append(pod_instance_name)
                replica_config['pod_instances'] = alive_pod_instances
                if replica_config.__contains__('isHPA'):
                    time_period = replica_config.get('time_period')
                    if not time_period:
                        time_period = 10
                    average_cpu, average_memory = 0, 0
                    count = 0
                    for pod_instance_name in alive_pod_instances:
                        pod_instance_config: dict = pods_dict[pod_instance_name]
                        cpu_usage_percent = pod_instance_config.get('cpu_usage_percent')
                        memory_usage_percent = pod_instance_config.get('memory_usage_percent')
                        if cpu_usage_percent and memory_usage_percent:
                            average_cpu += cpu_usage_percent
                            average_memory += memory_usage_percent
                            count += 1
                    cpu_limit = replica_config['metrics'].get('average_memory')
                    if not cpu_limit:
                        cpu_limit = 100
                    memory_limit = replica_config['metrics'].get('average_memory')
                    if not memory_limit:
                        memory_limit = 100
                    if count != 0:  # can calculate average
                        average_cpu /= count
                        average_memory /= count
                        if time.time() - replica_config['last_change_time'] > time_period:  # time to auto scale
                            replica_config['last_change_time'] = time.time()
                            print("average_cpu = {}, cpu_limit = {}, average_memory = {}, memory_limit = {},".format(average_cpu, cpu_limit, average_memory, memory_limit))
                            if average_cpu > cpu_limit or average_memory > memory_limit:
                                replica_config['spec']['replicas'] = min(replica_config['maxReplicas'],
                                                                         replica_config['spec']['replicas'] + 1)
                            else:
                                replica_config['spec']['replicas'] = max(replica_config['minReplicas'], replica_config['spec']['replicas'] - 1)
                            print("current HPA {} = {}".format(replica_config['instance_name'], replica_config['spec']['replicas']))

                expected_replica_number = replica_config['spec']['replicas']
                if expected_replica_number - len(alive_pod_instances) != 0:
                    print("Replica Set need create {} new instances".format(
                        str(expected_replica_number - len(alive_pod_instances))))
                while len(replica_config['pod_instances']) < expected_replica_number:
                    pod_config = copy.deepcopy(replica_config)
                    pod_config['kind'] = 'Pod'
                    pod_config['belong_to'] = replica_set_name
                    pod_config.pop('spec')
                    pod_config.pop('pod_instances')
                    json_data = json.dumps(pod_config)
                    r = requests.post(url='{}/Pod'.format(api_server_url), json=json_data)
                    pod_instance_name = json.loads(r.content.decode('UTF-8'))['instance_name']
                    print("pod_instance_name = {}".format(pod_instance_name))
                    replica_config['pod_instances'].append(pod_instance_name)
                while len(replica_config['pod_instances']) > expected_replica_number:
                    to_delete_pod_instance_name = replica_config['pod_instances'].pop()
                    r = requests.post(url='{}/Pod/{}/remove'.format(api_server_url, to_delete_pod_instance_name),
                                      json=json.dumps(dict()))
                # update the information into replica set config
                replica_config['status'] = 'Running'
                url = "{}/ReplicaSet/{}".format(api_server_url, replica_config['instance_name'])
                json_data = json.dumps(replica_config)
                r = requests.post(url=url, json=json_data)
            print("Current ReplicaSets are：{}".format(replica_set_dict['replica_sets_list']))
        except Exception as e:
            print('Connect API Server Failure!', e)
            continue


if __name__ == '__main__':
    main()
