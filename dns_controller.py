import copy
import logging
import time

import pika
import ast
import requests
import json
import kubedns
import utils
import yaml_loader
import worker_server


api_server_url = 'http://localhost:5050/'

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


def init_api_server():
    # todo: upload the api service here
    config: dict = yaml_loader.load("./dns/dns-nginx-server-replica-set.yaml")
    url = "http://127.0.0.1:5050/ReplicaSet"
    utils.post(url=url, config=config)

    config: dict = yaml_loader.load("./dns/dns-nginx-server-service.yaml")
    url = "http://127.0.0.1:5050/Service"
    utils.post(url=url, config=config)

    dns_config_dict = dict()
    dns_config_dict['dns-server-name'] = config['name']
    dns_config_dict['dns-server-ip'] = config['clusterIP']
    url = "http://127.0.0.1:5050/Dns/Config"
    utils.post(url=url, config=dns_config_dict)


def update_etc_hosts(hosts=True):
    """
    update etc hosts file in hosts machine or container machine
    dns_config_dict: dns config dict including
        dns_config_dict['etc-hosts-path'] = '/etc/hosts'
        dns_config_dict['etc-hosts-list'] = etc_hosts_list
        dns_config_dict['dns-hash']
    :param hosts: a flag indicating whether hosts or container
    :return:
    """
    dns_config_dict = utils.get_dns_config_dict(api_server_url=api_server_url)
    command = list()
    clear_command = "echo \"\" > %s" % dns_config_dict['etc-hosts-path']
    base_echo_command = "echo %s >> %s"

    command.append(clear_command)
    for ip2dns in dns_config_dict['etc-hosts-list']:
        command.append(base_echo_command % (ip2dns, dns_config_dict['etc-hosts-path']))
    print(command)
    if hosts is True:
        command = ";".join(command)
        command1 = "sudo systemctl restart network-manager"
        url = "{}/cmd".format(worker_server.worker_url)
        upload_cmd = dict()
        upload_cmd['cmd'] = ';'.join([command, command1])
        utils.post(url=url, config=upload_cmd)
    else:
        # TODO : Let Every Container of Every Pod to execute this command
        command = "/bin/sh -c \"{}\"".format(";".join(command))
        pod_dict = utils.get_pod_dict(api_server_url=api_server_url)
        for pod_instance in pod_dict:
            url = "{}/Pod/{}/{}".format(api_server_url, pod_instance, 'execute')
            upload_cmd = dict()
            upload_cmd['cmd'] = command
            utils.post(url=url, config=upload_cmd)
    return


def update_nginx_service():
    """
    update nginx service for dns, execute command `nginx -s reload` in each nginx service pod containers
    :param dns_config_dict: dns config including necessary info
    :param service_dict: service dict
    :return:
    """
    dns_config_dict = utils.get_dns_config_dict(api_server_url=api_server_url)
    service_dict = utils.get_service_dict(api_server_url=api_server_url)
    nginx_service_name = dns_config_dict['dns-server-name']
    for service_instance in service_dict['services_list']:
        if service_dict[service_instance]['name'] == nginx_service_name:
            for pod_instance in service_dict[service_instance]['pod_instances']:
                url = "http://127.0.0.1:5050/{}/execute".format(pod_instance)
                upload_cmd = dict()
                upload_cmd['cmd'] = "nginx -s reload"
                utils.post(url=url, config=upload_cmd)


def main():
    last_time = 0.0
    dns_hash = ''
    while True:
        dns_config_dict = utils.get_dns_config_dict(api_server_url=api_server_url)
        dns_dict = utils.get_dns_dict(api_server_url=api_server_url)

        # this should only execute once
        if dns_config_dict.get('dns-server-ip') is None:
            init_api_server()

        # every 30 seconds update whole dns
        # every dns config come in update whole dns
        current_time = time.time()
        if current_time - last_time <= 10 \
                and dns_config_dict.get('dns-hash') is not None \
                and dns_config_dict['dns-hash'] == hash('.'.join(dns_dict['dns_list'])):
            continue
        else:
            last_time = current_time
            service_dict = utils.get_service_dict(api_server_url=api_server_url)

        etc_hosts_list = list()
        for dns_instance in dns_dict['dns_list']:
            dns_config: dict = dns_dict[dns_instance]
            # add dns status
            dns_config['status'] = 'Created'
            # create dns conf file
            kubedns.create_dns(dns_config=dns_dict[dns_instance], service_dict=service_dict)
            # format /etc/hosts file string
            etc_hosts_list.append('%s %s' % (dns_config_dict['dns-server-ip'], dns_config['host']))

            url = "http://127.0.0.1:5050/Dns/{}".format(dns_config['instance_name'])
            utils.post(url=url, config=dns_config)

        dns_config_dict['etc-hosts-path'] = '/etc/hosts'
        dns_config_dict['etc-hosts-list'] = etc_hosts_list
        dns_config_dict['dns-hash'] = hash('.'.join(dns_dict['dns_list']))
        url = "http://127.0.0.1:5050/Dns/Config"
        utils.post(url=url, config=dns_config_dict)

        # update nginx service to exec `nginx -s reload`
        update_nginx_service()
        # update every container to exec `echo ... > /etc/hosts`
        update_etc_hosts(hosts=False)
        # update every node to exec `echo ... > /etc/hosts`
        update_etc_hosts(hosts=True)

        logging.info("当前的DNS为：{}".format(dns_dict['dns_list']))
        time.sleep(2)


if __name__ == '__main__':
    main()
