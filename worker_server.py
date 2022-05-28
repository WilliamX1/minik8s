import os

from flask import Flask, redirect, url_for, request, jsonify, Response
import json

import const
import utils
from werkzeug.utils import secure_filename

app = Flask(__name__)


# CORS(app, supports_credentials=True)

worker_url = const.worker0_url


@app.route('/cmd', methods=['POST'])
def execute_cmd():
    json_data = request.json
    config: dict = json.loads(json_data)
    cmd = config['cmd']
    # todo : run the cmd
    utils.exec_command(cmd, True)
    return json.dumps(dict()), 200


@app.route('/ServerlessFunction/<string:module_name>/upload', methods=['POST'])
def upload_script(module_name: str):
    # todo : add serverless logic here
    config = json.loads(request.json)
    print(config)
    data = config['script_data']
    print(request.files)
    f = open('./tmp/' + secure_filename('{}.py'.format(module_name)), 'w')
    f.write(data)
    f.close()
    os.system("cd tmp && docker build . -t {}".format(module_name))
    # we will build a docker image with tag: <instance_name>:latest here
    return 'file uploaded successfully'


def main():
    app.run(port=5051, processes=True)


if __name__ == '__main__':
    main()
