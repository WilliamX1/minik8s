import yaml.parser
from flask import Flask, redirect, url_for, request, jsonify, Response
from flask_cors import CORS
import base64
import os
import json
import pika

app = Flask(__name__)
# CORS(app, supports_credentials=True)
use_etcd = False
etcd_supplant = dict()


def broadcast_message(channel_name: str, message: str):
    connect = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connect.channel()
    # declare the name and type of the channel
    channel.exchange_declare(exchange=channel_name, exchange_type="fanout")
    # broadcast the message
    channel.basic_publish(exchange=channel_name, routing_key='', body=message.encode())
    connect.close()


@app.route('/pods', methods=["GET"])
def get_pods():
    if use_etcd:
        return "Not implemented", 404
    else:
        return json.dumps(etcd_supplant), 200


@app.route('/pods/<string:pod_name>', methods=['POST'])
def post_pod(pod_name: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    config['name'] = pod_name
    if use_etcd:
        return "Not implemented", 404
    else:
        if etcd_supplant.__contains__(pod_name):
            for key in config.keys():
                print("update {}[{}]".format(pod_name, key))
                etcd_supplant[pod_name][key] = config[key]
        else:
            print("create {}".format(pod_name))
            etcd_supplant[pod_name] = config

    broadcast_message('pods', config.__str__())
    return json.dumps(config), 200


if __name__ == '__main__':
    app.run(port=5050, processes=True)
