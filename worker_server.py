from flask import Flask, redirect, url_for, request, jsonify, Response
import json

app = Flask(__name__)
# CORS(app, supports_credentials=True)


@app.route('/cmd', methods=['POST'])
def execute_cmd():
    json_data = request.json
    config: dict = json.loads(json_data)
    cmd = config['cmd']
    # todo : run the cmd
    return json.dumps(dict()), 200

@app.route('/upload/serverless_script', methods=['POST'])
def upload_script():
    # todo : add serverless logic here
    pass

def main():
    app.run(port=5050, processes=True)

if __name__ == '__main__':
    main()
