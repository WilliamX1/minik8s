import copy
import logging
import time

import pika
import ast
import requests
import json
import kubedns
import utils

api_server_url = 'http://localhost:5050/'
nginx_service_ip = '10.11.22.33'


def init_nginx_service(dns_config_dict: dict):
    # TODO: Start an nginx service when starting
    """
    use ./dns/dns-nginx-server-pod.yaml and ./dns/dns-nginx-server-service.yaml to
    create nginx service and record clusterIP as `dns-server`
    :return:
    """
    return


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


if __name__ == '__main__':
    while True:
        try:
            r = requests.get(url=api_server_url + 'Dns')
            dns_dict = json.loads(r.content.decode('UTF-8'))
            r = requests.get(url=api_server_url + 'Service')
            service_dict = json.loads(r.content.decode('UTF-8'))
            r = requests.get(url=api_server_url + 'DnsConfig')
            dns_config_dict = json.loads(r.content.decode('UTF-8'))
            print(dns_dict)
            print(service_dict)
            print(dns_config_dict)
        except Exception as e:
            print('Connect API Server Failure')
            continue
        print("Current Dns : {}".format(dns_dict['dns_list']))
        current_sec = time.time()

        if dns_config_dict.get('dns-hash') is not None and dns_config_dict['dns-hash'] == hash('.'.join(dns_dict['dns_list'])):
            continue

        etc_hosts_str = ''
        for dns_name in dns_dict['dns_list']:
            dns_config: dict = dns_dict[dns_name]
            # add dns status
            dns_config['status'] = 'Created'
            # create dns conf file
            kubedns.create_dns(dns_config=dns_dict[dns_name], service_dict=service_dict)
            # format /etc/hosts file string
            etc_hosts_str += '%s %s\n' % (dns_config['nginx_service_ip'], dns_config['host'])

            url = "http://127.0.0.1:5050/Dns/{}".format(dns_config['instance_name'])
            json_data = json.dumps(dns_config)
            r = requests.post(url=url, json=json_data)

        dns_config_dict['etc-hosts-path'] = '/etc/hosts'
        dns_config_dict['etc-hosts-str'] = etc_hosts_str
        dns_config_dict['dns-hash'] = hash('.'.join(dns_dict['dns_list']))
        url = "http://127.0.0.1:5050/DnsConfig"
        json_data = json.dumps(dns_config_dict)
        r = requests.post(url=url, json=json_data)