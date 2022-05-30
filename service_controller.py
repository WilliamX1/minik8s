import copy
import logging
import time

import pika
import ast
import requests
import json
import kubeproxy
import utils
import const

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

api_server_url = const.api_server_url


def update_worker_server(service_config: dict, pods_dict: dict, behavior: str):
    # simulate at first to make service['iptables']
    if behavior == 'create':
        kubeproxy.create_service(service_config, pods_dict, True)
    elif behavior == 'update':
        kubeproxy.restart_service(service_config, pods_dict, True)
    elif behavior == 'remove':
        kubeproxy.rm_service(service_config, True)

    config = dict()
    config['service_config'] = service_config
    config['pods_dict'] = pods_dict
    for worker_url in const.worker_url_list:
        url = "{}/update_services/{}".format(worker_url['url'], behavior)
        utils.post(url=url, config=config)


def _create(service_dict: dict, service_config: dict, pods_dict: dict, update=False):
    # assign static IP if not assigned according to the config
    if service_config.get('clusterIP') is None:
        service_config['clusterIP'], _ = kubeproxy.alloc_service_clusterIP(service_dict)
    elif str(service_config['clusterIP']).find(str(kubeproxy.service_clusterIP_prefix)) != 0:
        logging.warning('Service cluster IP not starts with {}, trying to reallocate...'
                        .format(kubeproxy.service_clusterIP_prefix))
        service_config['clusterIP'], _ = kubeproxy.alloc_service_clusterIP(service_dict)

    selector: dict = service_config['selector']
    pod_instances = list()
    for pod_instance_name in pods_dict['pods_list']:
        pod_config = pods_dict[pod_instance_name]
        # only add running pod into service
        if not pod_config.__contains__('status') or pod_config['status'] != 'Running' or \
                not pod_config['metadata'].__contains__('labels'):
            continue
        pod_labels: dict = pod_config['metadata']['labels']
        matched = True
        # pod labels must be fully matched with the service selector
        if len(selector) != len(pod_labels):
            matched = False
        else:
            for key in selector:
                if pod_labels.__contains__(key) and pod_labels[key] == selector[key]:
                    continue
                else:
                    matched = False
                    break
        # if the pod contains all the label that the selector of the service requires.
        if matched:
            pod_instances.append(pod_instance_name)
    service_config['pod_instances'] = pod_instances
    logging.info("matched pod = ", pod_instances)
    # update every worker server iptables
    if update is False:
        update_worker_server(service_config, pods_dict, 'create')
    else:
        update_worker_server(service_config, pods_dict, 'update')
    # update status
    url = "{}/Service/{}/{}".format(api_server_url, service_config['instance_name'], 'running')
    utils.post(url=url, config=service_config)


def _update(service_dict: dict, service_config: dict, pods_dict: dict):
    _create(service_dict, service_config, pods_dict, True)


def _restart(service_dict: dict, service_config: dict, pods_dict: dict):
    _update(service_dict, service_config, pods_dict)


def _running():
    # do nothing
    pass


def _remove(service_config: dict, pods_dict: dict):
    # update every worker
    update_worker_server(service_config, pods_dict, 'remove')
    # update status
    url = "{}/Service/{}/{}".format(api_server_url, service_config['instance_name'], 'none')
    utils.post(url=url, config=service_config)


def _none():
    # do nothing
    pass


def main():
    while True:
        try:
            r = requests.get(url='{}/Service'.format(api_server_url))
            service_dict = json.loads(r.content.decode('UTF-8'))
            r = requests.get(url='{}/Pod'.format(api_server_url))
            pods_dict = json.loads(r.content.decode('UTF-8'))
        except Exception as e:
            logging.warning('Connect API Server Failure!')
            continue
        for service_name in service_dict['services_list']:
            service_config: dict = service_dict[service_name]
            status = service_config.get('status')
            print(service_config)
            if status is None:
                continue
            elif status == 'Creating':
                _create(service_dict=service_dict, service_config=service_config,
                        pods_dict=pods_dict)
            elif status == 'Updating':
                _update(service_dict=service_dict, service_config=service_config,
                        pods_dict=pods_dict)
            elif status == 'Restarting':
                _restart(service_dict=service_dict, service_config=service_config,
                         pods_dict=pods_dict)
            elif status == 'Running':
                _running()
            elif status == 'Removing':
                _remove(service_config=service_config, pods_dict=pods_dict)
            elif status == 'None':
                _none()
        print("Current Services are：{}".format(service_dict['services_list']))
        time.sleep(const.service_controller_flush_interval)


if __name__ == '__main__':
    main()
