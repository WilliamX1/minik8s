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


def update_etc_hosts(dns_config_dict: dict, hosts=True):
    """
    update etc hosts file in hosts machine or container machine
    :param dns_config_dict: dns config dict including
        dns_config_dict['etc-hosts-path'] = '/etc/hosts'
        dns_config_dict['etc-hosts-str'] = etc_hosts_str
        dns_config_dict['dns-hash']
    :param hosts: a flag indicating whether hosts or container
    :return:
    """
    if hosts is True:
        f = open(dns_config_dict['etc-hosts-path'], 'w')
        f.write(dns_config_dict['etc-hosts-str'])
        f.close()
        command = ["sudo", "systemctl", "restart", "network-manager"]
        utils.exec_command(command)  # restart to make /etc/hosts valid
    else:
        command = "/bin/sh -c %s > %s" \
                  % (dns_config_dict['etc-hosts-str'], dns_config_dict['etc-hosts-path'])
        # TODO : Let Every Container of Every Pod to execute this command
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
    for service_name in service_dict['services_list']:
        if service_dict[service_name]['name'] == nginx_service_name:
            for pod_name in service_dict[service_name]['pod_instances']:
                url = "http://127.0.0.1:5050/{}/execute".format(pod_name)
                upload_cmd = {'cmd': "/bin/sh -c %s > %s" % (dns_config_dict['etc-hosts-str'],
                                                            dns_config_dict['etc-hosts-path'])}
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

        etc_hosts_str = ''
        for dns_name in dns_dict['dns_list']:
            dns_config: dict = dns_dict[dns_name]
            # add dns status
            dns_config['status'] = 'Created'
            # create dns conf file
            kubedns.create_dns(dns_config=dns_dict[dns_name], service_dict=service_dict)
            # format /etc/hosts file string
            etc_hosts_str += '%s %s\n' % (dns_config_dict['dns-server-ip'], dns_config['host'])

            url = "http://127.0.0.1:5050/Dns/{}".format(dns_config['instance_name'])
            utils.post(url=url, config=dns_config)

        # update nginx service to exec `nginx -s reload`
        update_nginx_service()

        dns_config_dict['etc-hosts-path'] = '/etc/hosts'
        dns_config_dict['etc-hosts-str'] = etc_hosts_str
        dns_config_dict['dns-hash'] = hash('.'.join(dns_dict['dns_list']))
        url = "http://127.0.0.1:5050/Dns/Config"
        utils.post(url=url, config=dns_config_dict)

        time.sleep(2)


if __name__ == '__main__':
    main()