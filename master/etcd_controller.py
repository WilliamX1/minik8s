import os
import sys
import logging
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, os.path.pardir)
sys.path.append(os.path.join(BASE_DIR, '../helper'))
import utils, const, yaml_loader


def start_etcd():
    # start etcd
    yaml_path = os.path.join(ROOT_DIR, 'worker', 'nodes_yaml', 'master.yaml')
    etcd_info_config: dict = yaml_loader.load(yaml_path)
    API_SERVER_URL = etcd_info_config['API_SERVER_URL']
    ETCD_NAME = etcd_info_config['ETCD_NAME']
    ETCD_IP_ADDRESS = etcd_info_config['IP_ADDRESS']
    ETCD_INITIAL_CLUSTER = etcd_info_config['ETCD_INITIAL_CLUSTER']
    ETCD_INITIAL_CLUSTER_STATE = etcd_info_config['ETCD_INITIAL_CLUSTER_STATE']
    cmd1 = ['bash', const.ETCD_SHELL_PATH, ETCD_NAME, ETCD_IP_ADDRESS,
            ETCD_INITIAL_CLUSTER, ETCD_INITIAL_CLUSTER_STATE]
    utils.exec_command(cmd1, shell=False, background=True)
    logging.warning('Please make sure etcd is running successfully, waiting for 5 seconds...')
    time.sleep(6)
    cmd2 = '%s/worker/multi_machine/etcd/etcdctl put /coreos.com/network/config < ' \
           '%s/worker/multi_machine/configs/flannel-network-config.json' % (ROOT_DIR, ROOT_DIR)
    utils.exec_command(cmd2, shell=True)

    f = open(const.MASTER_API_SERVER_URL_PATH, 'w')
    f.write(API_SERVER_URL)
    f.close()
    return API_SERVER_URL


if __name__ == '__main__':
    start_etcd()
    print('Etcd is running...')
    while True:
        time.sleep(10)