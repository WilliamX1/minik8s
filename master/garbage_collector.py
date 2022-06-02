import time

import requests
import json

import sys, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
import utils, const

from api_server import get_api_server_url
api_server_url = get_api_server_url()


def main():
    while True:
        time.sleep(10)
        pods_dict = None
        try:
            r = requests.get(url="{}/Pod".format(api_server_url))
            pods_dict = json.loads(r.content.decode('UTF-8'))
        except Exception as e:
            print('Connect API Server Failure!')
            continue
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


if __name__ == '__main__':
    main()
