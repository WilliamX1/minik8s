import copy
import logging
import time

import pika
import ast
import requests
import json
import kubeproxy


api_server_url = 'http://localhost:5050/'


if __name__ == '__main__':
    while True:
        try:
            r = requests.get(url=api_server_url + 'Service')
            service_dict = json.loads(r.content.decode('UTF-8'))
            r = requests.get(url=api_server_url + 'Pod')
            pods_dict = json.loads(r.content.decode('UTF-8'))
            print(service_dict)
            print(pods_dict)
        except Exception as e:
            print('Connect API Server Failure!')
            continue
        print("当前的Service为：{}".format(service_dict['services_list']))
        current_sec = time.time()
        for service_name in service_dict['services_list']:
            service_config: dict = service_dict[service_name]
            # assign static IP if not assigned according to the config
            if service_config.get('clusterIP') is None:
                service_config['clusterIP'], _ = kubeproxy.alloc_service_clusterIP(service_dict)
            # add service status
            service_config['status'] = 'Created'
            # todo: where to add DNS logic ?

            selector: dict = service_config['selector']
            pod_instances = list()
            for pod_instance_name in pods_dict['pods_list']:
                pod_config = pods_dict[pod_instance_name]
                # only add running pod into service
                if not pod_config.__contains__('status') or pod_config['status'] != 'Running' or not pod_config['metadata'].__contains__('labels'):
                    continue
                pod_labels: dict = pod_config['metadata']['labels']
                matched = True

                # pod labels must be fully matched with the service selector
                if len(selector) != len(pod_labels):
                    matched = False
                else:
                    for key in selector:
                        if pod_labels.__contains__(key) and pod_labels[key] == selector[key]:
                            continue
                        else:
                            matched = False
                            break
                # if the pod contains all the label that the selector of the service requires.
                if matched:
                    pod_instances.append(pod_instance_name)
            service_config['pod_instances'] = pod_instances
            print("matched pod = ", pod_instances)

            # implement the service forward logic
            if service_config.get('iptables') is None:
                kubeproxy.create_service(service_config, pods_dict)
            else:
                kubeproxy.restart_service(service_config, pods_dict)

            url = "http://127.0.0.1:5050/Service/{}".format(service_config['instance_name'])
            json_data = json.dumps(service_config)
            r = requests.post(url=url, json=json_data)

        time.sleep(1)

