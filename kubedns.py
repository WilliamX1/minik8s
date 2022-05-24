import logging

import utils


dns_port = 80
conf_path = '$PWD/dns/conf'


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
                 "\tserver_name %s;\n\n" % (str(listen_port), host_name)
    format_str = comment_str + format_str
    location_str = "location %s {\n" \
                   "\tproxy_pass %s:%s;\n" \
                   "}\n"
    for p in paths:
        path = p['path']
        if path[0] != '/':  # path must be start with '/'
            path = '/' + path
        service_ip = p['service_ip']
        service_port = p['service_port']
        format_str += location_str % (path, service_ip, service_port)
    return format_str


def create_conf(listen_port: int, host_name: str, paths: list):
    format_str = format_conf(listen_port, host_name, paths)
    file_name = "%s.conf" % host_name
    file_path = '/'.join([conf_path, file_name])
    f = open(file_path, 'w')
    f.write(format_str)
    f.close()


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
            service_port: 801
    :param service_dict: service dict to find corresponding service
    :return:
    """
    name = dns_config['name']
    host = dns_config['host']
    paths = dns_config['paths']
    for p in paths:
        service_name = paths['service_name']
        for svc_name in service_dict['service_list']:
            if svc_name == service_name:
                p['service_ip'] = service_dict[svc_name]['ClusterIP']
                break
        if p.get('service_ip') is None:
            logging.warning('No Available Service %s Found for DNS' % service_name)
            return
    create_conf(listen_port=dns_port, host_name=host, paths=paths)


