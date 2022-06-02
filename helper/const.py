import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
FLANNEL_SHELL_PATH = os.path.join(ROOT_DIR, 'worker', 'multi_machine', 'scripts', 'flannel-shell.sh')
ETCD_SHELL_PATH = os.path.join(ROOT_DIR, 'worker', 'multi_machine', 'scripts', 'etcd-shell.sh')
DOCKER_SHELL_PATH = os.path.join(ROOT_DIR, 'worker', 'multi_machine', 'scripts', 'docker-shell.sh')

# a flag indicating whether you use etcd to store machine ip information
# if no, define and get api_server_url and worker_url_list from here
# if yes, define and get api_server_url and worker_url_list into etcd

api_server_file_path: str = os.path.join(ROOT_DIR, 'userland', '.api_server_url')
# api_server_ip: str = 'http://192.168.1.12'
# api_server_port: str = '5050'
# api_server_url: str = 'http://192.168.1.12:5050'  # api server ip address locally

service_controller_flush_interval: float = 2.0
service_clusterIP_prefix: int = 18  # every service's clusterIP must start with 18
service_iptables_save_path: str = "/".join(
    [ROOT_DIR, 'worker', 'sources', 'iptables-save'])  # save iptables into this file

dns_controller_flush_interval: float = 2.0
dns_port: int = 80
dns_conf_path: str = os.path.join(ROOT_DIR, 'userland', 'dns', 'nginx', 'conf')



