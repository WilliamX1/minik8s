import yaml.parser
from flask import Flask, redirect, url_for, request, jsonify, Response
from flask_cors import CORS
import base64
import os
import json
import pika
import uuid

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


@app.route('/pods', methods=['GET', 'POST'])
def get_pods():
    if request.method == 'GET':
        if use_etcd:
            return "Not implemented", 404
        else:
            return json.dumps(etcd_supplant), 200
    elif request.method == 'POST':
        json_data = request.json
        config: dict = json.loads(json_data)
        instance_name = config['name'] + uuid.uuid1().__str__()
        config['instance_name'] = instance_name
        if use_etcd:
            return "Not implemented", 404
        else:
            etcd_supplant[instance_name] = config
            print("create {}".format(instance_name))

        broadcast_message('pods', config.__str__())
        return "Successfully create instance {}".format(instance_name), 200



@app.route('/pods/<string:instance_name>', methods=['POST'])
def post_pod(instance_name: str):
    json_data = request.json
    config: dict = json.loads(json_data)
    if use_etcd:
        return "Not implemented", 404
    else:
        if etcd_supplant.__contains__(instance_name):
            for key in config.keys():
                print("update {}[{}]".format(instance_name, key))
                etcd_supplant[instance_name][key] = config[key]
        else:
            return "Instance Not Fount", 404

    broadcast_message('pods', config.__str__())
    return json.dumps(config), 200


if __name__ == '__main__':
    app.run(port=5050, processes=True)
