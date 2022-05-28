import os


# a flag indicating whether you use etcd to store machine ip information
# if no, define and get api_server_url and worker_url_list from here
# if yes, define and get api_server_url and worker_url_list into etcd
use_etcd: bool = False
api_server_url: str = 'http://localhost:5050'  # api server ip address locally
worker_url_list: list = ['http://localhost:5051']  # worker0 url

service_controller_flush_interval: float = 2.0
service_clusterIP_prefix: int = 18  # every service's clusterIP must start with 18
service_iptables_save_path: str = "/".join(
    [os.getcwd(), 'sources', 'iptables-save'])  # save iptables into this file

dns_controller_flush_interval: float = 2.0
dns_port: int = 80
dns_conf_path: str = '/'.join([os.getcwd(), 'dns', 'conf'])


