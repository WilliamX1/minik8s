import os

from flask import Flask, redirect, url_for, request, jsonify, Response
import json
import utils
from werkzeug.utils import secure_filename

app = Flask(__name__)


# CORS(app, supports_credentials=True)

worker_url = "http://127.0.0.1:5051"


@app.route('/cmd', methods=['POST'])
def execute_cmd():
    json_data = request.json
    config: dict = json.loads(json_data)
    cmd = config['cmd']
    # todo : run the cmd
    utils.exec_command(cmd)
    return json.dumps(dict()), 200


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
