import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
FLANNEL_PATH = os.path.join(ROOT_DIR, 'worker', 'multi_machine', 'flanneld')
ETCD_SHELL_PATH = os.path.join(ROOT_DIR, 'worker', 'multi_machine', 'scripts', 'etcd-shell.sh')
DOCKER_SHELL_PATH = os.path.join(ROOT_DIR, 'worker', 'multi_machine', 'scripts', 'docker-shell.sh')
API_SERVER_URL_PATH: str = os.path.join(ROOT_DIR, 'userland', '.api_server_url')
MASTER_API_SERVER_URL_PATH: str = os.path.join(ROOT_DIR, 'master', '.api_server_url')


service_controller_flush_interval: float = 2.0
service_clusterIP_prefix: list = [192, 168]  # every service's clusterIP must start with 18
service_iptables_save_path: str = "/".join(
    [ROOT_DIR, 'worker', 'sources', 'iptables-save'])  # save iptables into this file

dns_controller_flush_interval: float = 2.0
dns_port: int = 80
DNS_CONF_PATH: str = os.path.join(ROOT_DIR, 'master', 'dns', 'nginx', 'conf')
DNS_REPLICASET_PATH: str = os.path.join(ROOT_DIR, 'master', 'dns', 'dns-nginx-server-replica-set.yaml')
DNS_SERVICE_PATH: str = os.path.join(ROOT_DIR, 'master', 'dns', 'dns-nginx-server-service.yaml')



