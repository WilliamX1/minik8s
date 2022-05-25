from flask import Flask, redirect, url_for, request, jsonify, Response
import json
import utils

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


@app.route('/upload/serverless_script', methods=['POST'])
def upload_script():
    # todo : add serverless logic here
    pass


def main():
    app.run(port=5051, processes=True)


if __name__ == '__main__':
    main()
