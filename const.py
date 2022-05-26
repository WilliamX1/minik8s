import os


PI = 3.14  # for test
api_server_url = 'http://localhost:5050'  # api server ip address locally
worker_url_list = ['http://localhost:5051']  # worker0 url

service_clusterIP_prefix = 18  # every service's clusterIP must start with 18
service_iptables_save_path = "/".join(
    [os.getcwd(), 'sources', 'iptables-save'])  # save iptables into this file

dns_controller_flush_interval = 2.0
dns_controller_update_interval = 60.0
dns_port = 80
dns_conf_path = '/'.join([os.getcwd(), 'dns', 'conf'])


