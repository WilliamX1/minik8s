import logging
import os

from flask import Flask, request
import json

import sys, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
import utils, const
from werkzeug.utils import secure_filename
from worker import kubeproxy

app = Flask(__name__)

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


# CORS(app, supports_credentials=True)

worker_port = const.worker_url_list[0]['port']
worker_url = const.worker_url_list[0]['url']
init: bool = False


@app.route('/cmd', methods=['POST'])
def execute_cmd():
    json_data = request.json
    config: dict = json.loads(json_data)
    cmd = config['cmd']
    utils.exec_command(cmd, True)
    return json.dumps(dict()), 200


@app.route('/update_services/<string:behavior>', methods=['POST'])
def update_services(behavior: str):
    print("Update Service %s" % behavior)
    json_data = request.json
    config: dict = json.loads(json_data)
    service_config = config['service_config']
    pods_dict = config['pods_dict']
    global init
    if init is False:
        init = True
        kubeproxy.init_iptables()

    if behavior == 'create':
        kubeproxy.sync_service(service_config, pods_dict)
    elif behavior == 'update':
        kubeproxy.sync_service(service_config, pods_dict)
    elif behavior == 'remove':
        kubeproxy.rm_service(service_config)
    return json.dumps(service_config), 200


@app.route('/ServerlessFunction/<string:instance_name>/upload', methods=['POST'])
def upload_script(instance_name: str):
    # todo : add serverless logic here
    config = json.loads(request.json)
    print(config)
    data = config['script_data']
    print(request.files)
    f = open('./tmp/' + secure_filename('{}.py'.format(module_name)), 'w')
    f.write(data)
    f.close()
    os.system("cd tmp && docker build . -t {}".format(module_name))
    # import docker
    #
    # docker_client = docker.from_env(version='1.25', timeout=5)
    # docker_client.images.build(path="./tmp")
    # we will build a docker image with tag: <instance_name>:latest here
    return 'file uploaded successfully'


def main():
    app.run(host='0.0.0.0', port=worker_port, processes=True)


if __name__ == '__main__':
    main()
