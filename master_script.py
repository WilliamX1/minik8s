import json
from multiprocessing import Process, Pool
import time

import requests

import scheduler
import replica_set_controller
import api_server
import node_controller
import service_controller
import dns_controller
import yaml_loader


def init_api_server():
    # todo: upload the api service here
    time.sleep(1)   # wait for api server to start
    config: dict = yaml_loader.load("./xhd-service.yaml")
    object_name = config['name']
    url = "http://127.0.0.1:5050/Service"
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)

if __name__ == '__main__':
    pool = Pool()
    # make sure that the func has a good error handler to avoid exit
    pool.apply_async(func=api_server.main)
    init_api_server()
    pool.apply_async(func=service_controller.main)
    pool.apply_async(func=dns_controller.main)
    pool.apply_async(func=replica_set_controller.main)
    pool.apply_async(func=node_controller.main)
    pool.apply_async(func=scheduler.main)
    pool.close()
    pool.join()