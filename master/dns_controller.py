import logging
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../userland'))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
sys.path.append(os.path.join(BASE_DIR, '../worker'))
import kubedns

import yaml_loader, const, utils


ROOT_DIR = os.path.join(BASE_DIR, os.path.pardir)
yaml_path = os.path.join(ROOT_DIR, 'worker', 'nodes_yaml', 'master.yaml')
etcd_info_config: dict = yaml_loader.load(yaml_path)
api_server_url = etcd_info_config['API_SERVER_URL']


logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


def init_dns_server():
    """
    init dns server when starting, mainly doing things:
    - start a replicaset (image: nginx)
    - start a service (provide a cluster IP for reverse proxy), default is `18.1.1.1`
    - update dns_config_dict, store this service cluster IP into etcd
    - start a dns for this service, default is 1`ns-nginx-server-service`
    :return: None
    """
    config: dict = yaml_loader.load(const.DNS_REPLICASET_PATH)
    url = "{}/ReplicaSet".format(api_server_url)
    utils.post(url=url, config=config)

    config: dict = yaml_loader.load(const.DNS_SERVICE_PATH)
    url = "{}/Service".format(api_server_url)
    utils.post(url=url, config=config)

    dns_config_dict = dict()
    dns_config_dict['dns-server-name'] = config['name']
    dns_config_dict['dns-server-ip'] = config['clusterIP']
    url = "{}/Dns/Config".format(api_server_url)
    utils.post(url=url, config=dns_config_dict)


def update_etc_hosts(hosts=True):
    """
    update etc hosts file in every host's machine or container machine
    dns_config_dict: dns config dict including
        dns_config_dict['etc-hosts-path'] = '/etc/hosts'
        dns_config_dict['etc-hosts-list'] = etc_hosts_list
        dns_config_dict['dns-hash']: used for record whether dns changed
    :param hosts: a flag indicating whether hosts or container
    :return: None
    """
    dns_config_dict = utils.get_dns_config_dict(api_server_url=api_server_url)
    command = list()
    clear_command = "echo 127.0.0.1 localhost > {}".format(dns_config_dict['etc-hosts-path'])
    base_echo_command = "echo {} >> {}"
    print(dns_config_dict)
    command.append(clear_command)
    for ip2dns in dns_config_dict['etc-hosts-list']:
        command.append(base_echo_command.format(ip2dns, dns_config_dict['etc-hosts-path']))
    if hosts is True:
        # Let Host Machine to execute this command
        command1 = "sudo systemctl restart network-manager"
        command.append(command1)
        worker_url_list = utils.get_worker_url_list(api_server_url=api_server_url)
        for worker_url in worker_url_list:
            url = "{}/cmd".format(worker_url)  # TODO: need to change
            upload_cmd = dict()
            upload_cmd['cmd'] = command
            utils.post(url=url, config=upload_cmd)
    else:
        # Let Every Container of Every Pod to execute this command
        # command = "/bin/sh -c \"{}\"".format(";".join(command))
        pod_dict = utils.get_pod_dict(api_server_url=api_server_url)
        print('pod_dict')
        print(pod_dict)
        for pod_instance in pod_dict['pods_list']:
            url = "{}/Pod/{}/{}".format(api_server_url, pod_instance, 'execute')
            upload_cmd = dict()
            upload_cmd['cmd'] = command
            utils.post(url=url, config=upload_cmd)


def update_nginx_service():
    """
    update nginx service for dns, execute command `nginx -s reload` in each nginx service pod containers
    :return:
    """
    dns_config_dict = utils.get_dns_config_dict(api_server_url=api_server_url)
    service_dict = utils.get_service_dict(api_server_url=api_server_url)
    nginx_service_name = dns_config_dict['dns-server-name']
    for service_instance in service_dict['services_list']:
        if service_dict[service_instance]['name'] == nginx_service_name:
            for pod_instance in service_dict[service_instance]['pod_instances']:
                print(pod_instance)
                url = "{}/Pod/{}/{}".format(api_server_url, pod_instance, 'execute')
                upload_cmd = dict()
                upload_cmd['cmd'] = ["nginx -s reload"]
                utils.post(url=url, config=upload_cmd)


def _create(dns_config: dict, dns_config_dict: dict, service_dict: dict, etc_hosts_list: list):
    # create dns conf file
    kubedns.create_dns(dns_config=dns_config, service_dict=service_dict)
    # format /etc/hosts file string
    etc_hosts_list.append('{} {}'.format(dns_config_dict['dns-server-ip'], dns_config['host']))
    # post requests to api_server
    url = "{}/Dns/{}/{}".format(api_server_url, dns_config['instance_name'], 'running')
    utils.post(url=url, config=dns_config)


def _update(dns_config: dict, dns_config_dict: dict, service_dict: dict, etc_hosts_list: list):
    _create(dns_config, dns_config_dict, service_dict, etc_hosts_list)


def _restart(dns_config: dict, dns_config_dict: dict, service_dict: dict, etc_hosts_list: list):
    _update(dns_config, dns_config_dict, service_dict, etc_hosts_list)


def _running(dns_config: dict, dns_config_dict: dict, etc_hosts_list: list):
    # format /etc/hosts file string
    etc_hosts_list.append('{} {}'.format(dns_config_dict['dns-server-ip'], dns_config['host']))
    pass


def _remove(dns_config: dict):
    kubedns.rm_dns(dns_config=dns_config)
    url = "{}/Dns/{}/{}".format(api_server_url, dns_config['instance_name'], 'none')
    utils.post(url=url, config=dns_config)


def _none():
    # do nothing
    pass


def main():
    while True:
        time.sleep(const.dns_controller_flush_interval)
        try:
            dns_config_dict = utils.get_dns_config_dict(api_server_url=api_server_url)
            dns_dict = utils.get_dns_dict(api_server_url=api_server_url)
            service_dict = utils.get_service_dict(api_server_url=api_server_url)
        except Exception as e:
            print('Connect API Server Failure!', e)
            continue
        # this should only execute once
        if dns_config_dict is None:
            continue
        if dns_config_dict.get('dns-server-ip') is None:
            init_dns_server()

        # every dns config come in update whole dns
        """
        current_time = time.time()
        if current_time - last_time <= const.dns_controller_update_interval \
                and dns_config_dict.get('dns-hash') is not None \
                and dns_config_dict['dns-hash'] == hash('.'.join(dns_dict['dns_list'])):
            continue
        else:
            last_time = current_time
            service_dict = helper.get_service_dict(api_server_url=api_server_url)
        """

        etc_hosts_list = list()
        update_flag = False  # if all the dns status is not creating or updating
        for dns_instance in dns_dict['dns_list']:
            dns_config: dict = dns_dict[dns_instance]
            # dns status
            status = dns_config.get('status')
            if status is None:
                continue
            elif status == 'Creating':
                update_flag = True
                _create(dns_config=dns_config, dns_config_dict=dns_config_dict,
                        service_dict=service_dict, etc_hosts_list=etc_hosts_list)
            elif status == 'Updating':
                update_flag = True
                _update(dns_config=dns_config, dns_config_dict=dns_config_dict,
                        service_dict=service_dict, etc_hosts_list=etc_hosts_list)
            elif status == 'Restarting':
                update_flag = True
                _restart(dns_config=dns_config, dns_config_dict=dns_config_dict,
                         service_dict=service_dict, etc_hosts_list=etc_hosts_list)
            elif status == 'Running':
                _running(dns_config=dns_config, dns_config_dict=dns_config_dict,
                         etc_hosts_list=etc_hosts_list)
            elif status == 'Removing':
                _remove(dns_config=dns_config)
            elif status == 'None':
                _none()
        # Update dns_config_dict, focus on 'dns-hash' please
        dns_config_dict['etc-hosts-path'] = '/etc/hosts'
        dns_config_dict['etc-hosts-list'] = etc_hosts_list
        dns_config_dict['dns-hash'] = hash('.'.join(dns_dict['dns_list']))
        url = "{}/Dns/Config".format(api_server_url)
        utils.post(url=url, config=dns_config_dict)
        if update_flag is True:
            # update nginx service to exec `nginx -s reload`
            update_nginx_service()
            # update every container to exec `echo ... > /etc/hosts`
            update_etc_hosts(hosts=False)
            # update every node to exec `echo ... > /etc/hosts`
            update_etc_hosts(hosts=True)

        logging.info("Current DNS are: {}".format(dns_dict['dns_list']))


if __name__ == '__main__':
    main()
