import json
from multiprocessing import Process, Pool
import time

import requests

import const
import scheduler
import replica_set_controller
import api_server
import node_controller
import service_controller
import dns_controller
import yaml_loader
import garbage_collector
import os


api_server_url = const.api_server_url


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
    pool.apply_async(func=node_controller.main)
    pool.apply_async(func=replica_set_controller.main)
    pool.close()
    pool.join()
