import copy
import time

import pika
import ast
import requests
import json

api_server_url = 'http://localhost:5050/'


if __name__ == '__main__':
    while True:
        try:
            r = requests.get(url=api_server_url + 'Service')
            service_dict = json.loads(r.content.decode('UTF-8'))
            r = requests.get(url=api_server_url + 'Pod')
            pods_dict = json.loads(r.content.decode('UTF-8'))
        except Exception as e:
            print('Connect API Server Failure!')
            continue
        print("当前的Service为：{}".format(service_dict['services_list']))
        current_sec = time.time()
        for service_name in service_dict['services_list']:
            # todo: assign static IP if not assigned according to the config
            # todo: add service status
            # todo: where to implement the service forward logic ?
            # todo: where to add DNS logic ?
            service_config = service_dict[service_name]
            selector: dict = service_config['selector'][0]
            pod_instances = list()
            for pod_instance_name in pods_dict['pods_list']:
                pod_config = pods_dict[pod_instance_name]
                # only add running pod into service
                if not pod_config.__contains__('status') or pod_config['status'] != 'Running' or not pod_config['metadata'].__contains__('labels'):
                    continue
                pod_labels = pod_config['metadata']['labels'][0]
                matched = True
                for key in selector.keys():
                    # todo: handle complex selector here
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
            url = "http://127.0.0.1:5050/Service/{}".format(service_config['instance_name'])
            json_data = json.dumps(service_config)
            r = requests.post(url=url, json=json_data)

        time.sleep(1)

