import json

from flask import Flask, request
import importlib
import os

app = Flask(__name__)
job_id = None


@app.route('/submit', methods=['POST'])
def submit():
    global job_id
    config = json.loads(request.json)
    module_name = config['module_name']
    status = dict()
    if job_id is None:
        result = os.popen('/bin/bash /upload.sh {}'.format(module_name))
        lines = result.readlines()
        try:
            job_id = lines[-5].split()[-1]
            status['status'] = 'Success'
            status['job_id'] = job_id
            print("job_id = ", job_id)
        except Exception as e:
            status['status'] = 'Failed'
            print("failed", lines)
    else:
        status['status'] = 'Success'
        status['job_id'] = job_id
    return json.dumps(status), 200


@app.route('/download', methods=['POST'])
def download():
    global job_id
    return_data = dict()
    result = os.popen('/bin/bash /download.sh')
    print("result = ", result)
    files_list = list()
    files = []
    for _, _, a in os.walk('/data'):
        files = a
    for file in files:
        file_abs_path = os.path.join('/data', file)
        files_list.append(file)
        with open(file_abs_path) as f:
            return_data[file] = f.read()
    return_data['files_list'] = files_list
    return json.dumps(return_data), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5054, processes=True)
