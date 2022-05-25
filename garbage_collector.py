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

def main():
    while True:
        time.sleep(10)
        pods_dict = None
        try:
            r = requests.get(url=api_server_url + 'Pod')
            pods_dict = json.loads(r.content.decode('UTF-8'))
        except Exception as e:
            print('Connect API Server Failure!')
            continue
        for pod_instance_name in pods_dict['pods_list']:
            # print("status = ", pods_dict[pod_instance_name].get('status'))
            if pods_dict[pod_instance_name].get('status') == 'Schedule Failed':
                r = requests.post(url=api_server_url + 'Pod/{}/delete'.format(pod_instance_name), json=json.dumps(dict()))

if __name__ == '__main__':
    main()