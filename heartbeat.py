import memcache
import time
import ast

import const
from kubelet import node_name
import json
import requests

share = memcache.Client(["127.0.0.1:11211"], debug=True)
api_server_url = const.api_server_url
url = "{}/heartbeat".format(api_server_url)

if __name__ == '__main__':
    while True:
        time.sleep(2)
        if share.get('status') is None:
            continue
        status = ast.literal_eval(share.get('status'))
        heartbeat = {'node': node_name, 'pods': status['pods'], 'ReplicaSets': status['ReplicaSets'],
                     'cpu': status['cpu'], 'mem': status['mem']}

        json_data = json.dumps(heartbeat)
        print('{} send heartbeat'.format(node_name))
        print(heartbeat)
        r = requests.post(url=url, json=json_data)
