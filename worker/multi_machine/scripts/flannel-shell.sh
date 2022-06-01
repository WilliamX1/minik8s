#!/bin/bash

BASE_DIR=$(cd $(dirname $0); pwd)
IP_ADDRESS=$1
ETCD_ENDPOINTS=$2

# config flannel
${BASE_DIR}/../etcd/etcdctl put /coreos.com/network/config < ${BASE_DIR}/../configs/flannel-network-config.json

# start flanneld
sudo ${BASE_DIR}/../flanneld -iface=ens3