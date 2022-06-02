import json

from flask import Flask, request
import importlib
import os

app = Flask(__name__)
job_id = None


@app.route('/submit', methods=['GET', 'POST'])
def execute_function():
    global job_id
    module_name = 'add'
    status = dict()
    if job_id is None:
        result = os.popen('/bin/bash ./a.sh {}'.format(module_name))
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


@app.route('/result', methods=['GET'])
def execute_function():
    global job_id
    status = dict()
    if job_id is None:
        result = os.popen('/bin/bash ./a.sh')
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5052, processes=True)
