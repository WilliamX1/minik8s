#!/bin/bash

BASE_DIR=$(cd $(dirname $0); pwd)
IP_ADDRESS=$1

# config flannel
${BASE_DIR}/../etcd/etcdctl set /coreos.com/network/config < ${BASE_DIR}/../configs/flannel-network-config.json

# start flanneld
sudo ${BASE_DIR}/../flanneld -iface=${IP_ADDRESS}