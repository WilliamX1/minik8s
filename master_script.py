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
import garbage_collector
import os


def init_api_server():
    # todo: upload the api service here
    time.sleep(1)   # wait for api server to start
    config: dict = yaml_loader.load("./dns/dns-nginx-server-service.yaml")
    url = "http://127.0.0.1:5050/Service"
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)

    config: dict = yaml_loader.load("./dns/dns-nginx-server-replica-set.yaml")
    url = "http://127.0.0.1:5050/ReplicaSet"
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)

if __name__ == '__main__':
    # os.system("python api_server.py &")
    # os.system("python scheduler.py &")
    # os.system("python garbage_collector.py &")
    # os.system("python service_controller.py &")
    # os.system("python dns_controller.py &")
    # os.system("python replica_set_controller.py &")
    # os.system("python node_controller.py &")

    pool = Pool()
    # make sure that the func has a good error handler to avoid exit
    #
    pool.apply_async(func=api_server.main)
    pool.apply_async(func=scheduler.main)
    pool.apply_async(func=garbage_collector.main)
    pool.apply_async(func=service_controller.main)
    pool.apply_async(func=dns_controller.main)
    pool.apply_async(func=replica_set_controller.main)
    pool.apply_async(func=node_controller.main)

    init_api_server()
    pool.close()
    pool.join()