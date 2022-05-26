import os

from flask import Flask, redirect, url_for, request, jsonify, Response
import json

import const
import utils
from werkzeug.utils import secure_filename
import kubeproxy

app = Flask(__name__)


# CORS(app, supports_credentials=True)

worker_url = const.worker_url_list[0]


@app.route('/cmd', methods=['POST'])
def execute_cmd():
    json_data = request.json
    config: dict = json.loads(json_data)
    cmd = config['cmd']
    utils.exec_command(cmd, True)
    return json.dumps(dict()), 200


@app.route('/update_iptables', methods=['POST'])
def update_iptables():
    json_data = request.json
    config: dict = json.loads(json_data)
    service_config = config['service_config']
    pods_dict = config['pods_dict']
    # implement the service forward logic
    if service_config.get('iptables') is None:
        kubeproxy.create_service(service_config, pods_dict)
    else:
        kubeproxy.restart_service(service_config, pods_dict)


@app.route('/ServerlessFunction/<string:instance_name>/upload', methods=['POST'])
def upload_script(instance_name: str):
    # todo : add serverless logic here
    f = request.files['file']
    print(request.files)
    f.save('./tmp/' + secure_filename('{}.py'.format(instance_name)))
    os.system("cd tmp && docker build . -t {}".format(instance_name))
    # we will build a docker image with tag: <instance_name>:latest here
    return 'file uploaded successfully'


def main():
    app.run(port=5051, processes=True)


if __name__ == '__main__':
    main()
