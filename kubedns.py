import logging
import os
import time

import const

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

dns_port = const.dns_port
conf_path = const.dns_conf_path


def format_conf(listen_port: int, host_name: str, paths: list):
    """
    format a conf file for nginx container, for example:

    # minik8s.conf
    server {
        listen 80;
        server_name minik8s.com;

        location /subpath {
            proxy_pass http://10.119.22.33:801;
        }
    }

    :return: format string which can be written into a file directly
    """
    comment_str = "# %s.conf\n" % host_name
    format_str = "server {\n" \
                 "\tlisten %s;\n" \
                 "\tserver_name %s;\n" \
                 "\tindex index.html index.htm;\n\n" % (str(listen_port), host_name)
    format_str = comment_str + format_str
    location_str = "\tlocation %s/ {\n" \
                   "\t\tproxy_pass http://%s:%s/;\n" \
                   "\t}\n"
    for p in paths:
        path = p['path']
        if path[0] != '/':  # path must be start with '/'
            path = '/' + path
        service_ip = p['service_ip']
        service_port = p['service_port']
        format_str += location_str % (path, service_ip, service_port)
    format_str += "}"
    return format_str


def create_conf(listen_port: int, host_name: str, paths: list):
    """
    create a conf file in the folder ./minik8s/dns/conf
    :param listen_port: must be 80 here
    :param host_name: like `minik8s.com`
    :param paths: subpath include `path`, `service_name` and `service_port`
    :return:
    """
    format_str = format_conf(listen_port, host_name, paths)
    file_name = "%s.conf" % host_name
    file_path = '/'.join([conf_path, file_name])
    f = open(file_path, 'w')
    f.write(format_str)
    f.close()
    return file_path


def create_dns(dns_config: dict, service_dict: dict):
    """
    create a dns by create a `.conf` file and restart docker
    :param dns_config: dns config file such as:
        kind: Dns
        name: xhd-dns
        host: 'minik8s.com'
        paths:
          - path: '/dd'
            service_name: 'xhd-service'
            service_port: 80
    :param service_dict: service dict to find corresponding service
    :return:
    """
    name = dns_config['name']
    host = dns_config['host']
    paths = dns_config['paths']
    for p in paths:
        service_name = p['service_name']
        for svc_name in service_dict['services_list']:
            if service_dict[svc_name]['name'] == service_name:
                p['service_ip'] = service_dict[svc_name]['clusterIP']
                break
        if p.get('service_ip') is None:
            logging.warning('Currently No Available Service {} Found for DNS'.format(service_name))
            return False
    dns_config['conf-path'] = create_conf(listen_port=dns_port, host_name=host, paths=paths)
    return True


def describe_dns(dns_config: dict, dns_instance_name: dict, title=False):
    """
    describe a dns showing its info
    | name | status | created time | host | path | service_name | service_port |
    :param dns_config: dns config from etcd
    :param dns_instance_name: dns instance name with its suffix
    :param title: a flag indicating whether to show the bar
    :return: None
    """
    if title is True:
        print("|{0:10}|{1:10}|{2:16}|{3:16}|{4:8}|{5:8}|{6:4}".format('name', 'status', 'created time',
                                                              'host', 'path', 'service_name', 'service_port'))
    dns_status = dns_config['status']
    created_time = int(time.time() - dns_config['created_time'])
    created_time = str(created_time // 60) + "m" + str(created_time % 60) + 's'
    host = dns_config['host']
    paths: list = dns_config['paths']
    if paths is None:
        print(f"{dns_instance_name:100}{dns_status:30}{created_time.strip():30}"
              f"{host:12}{'<none>':15}{'<none>':15}{'<none>':15}")
    else:
        for p in paths:
            print(f"{dns_instance_name:100}{dns_status:30}{created_time.strip():30}"
                  f"{host:12}{p['path']:15}{p['service_name']:15}{p['service_port']:15}")


def show_dns(dns_dict: dict):
    """
    get all dns running state
    :param dns_dict:
    :return: a list of dns
    """
    print("|{0:10}|{1:10}|{2:16}|{3:8}|{4:8}|{5:8}|{6:4}".format('name', 'status', 'created time',
                                                          'host', 'path', 'service_name', 'service_port'))
    for dns_instance_name in dns_dict['dns_list']:
        dns_config = dns_dict[dns_instance_name]
        describe_dns(dns_config=dns_config, dns_instance_name=dns_instance_name, title=False)


def rm_dns(dns_config: dict):
    """
    delete dns config file
    :param dns_config: dns config
    :return: None
    """
    os.remove(dns_config['conf-path'])
