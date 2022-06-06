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
        time.sleep(10)
        pods_dict = None
        try:
            # logic 1: handle schedule failed pod
            r = requests.get(url="{}/Pod".format(api_server_url))
            pods_dict = json.loads(r.content.decode('UTF-8'))
            for pod_instance_name in pods_dict['pods_list']:
                # print("status = ", pods_dict[pod_instance_name].get('status'))
                if pods_dict.get(pod_instance_name) and pods_dict[pod_instance_name].get('status') == 'Schedule Failed':
                    r = requests.post(url='{}/Pod/{}/delete'.format(api_server_url, pod_instance_name),
                                      json=json.dumps(dict()))
                if pods_dict.get(pod_instance_name) and pods_dict[pod_instance_name].get('status') == 'Ready to Create':
                    time_period = int(time.time() - pods_dict[pod_instance_name]['created_time'])
                    # print(time_period)
                    if time_period > 20:
                        r = requests.post(url='{}/Pod/{}/delete'.format(api_server_url, pod_instance_name),
                                          json=json.dumps(dict()))
            # logic 2: handle scale to zero
            r = requests.get(url='{}/Function'.format(api_server_url))
            functions_dict = json.loads(r.content.decode('UTF-8'))
            for function_name in functions_dict['functions_list']:
                function_config = functions_dict.get(function_name)
                if function_config and function_config.__contains__('pod_instances'):
                    for pod_instance_name in function_config['pod_instances']:
                        r = requests.get('{}/Pod/{}'.format(api_server_url, pod_instance_name))
                        pod_config: dict = json.loads(r.content.decode())
                        if pod_config and pod_config.get('status') == 'Running':
                            last_activated_time = pod_config['last_activated_time']
                            if time.time() - last_activated_time < 5:
                                print("serverless pod {} has lots of requests, try add pods!".format(pod_instance_name))
                                r = requests.post("{}/Function/{}/add_instance".format(api_server_url, function_name), json=json.dumps(dict()))
                            if time.time() - last_activated_time > 30:
                                print("serverless pod {} timeout, try remove it !".format(pod_instance_name))
                                r = requests.post("{}/Pod/{}/remove".format(api_server_url, pod_instance_name), json=json.dumps(dict()))

        except Exception as e:
            print('Connect API Server Failure!')
            print(e.__str__())
            continue



if __name__ == '__main__':
    main()
