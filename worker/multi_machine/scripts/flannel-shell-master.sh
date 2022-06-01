#!/bin/bash

BASE_DIR=$(cd $(dirname $0); pwd)

# config flannel
${BASE_DIR}/../etcd/etcdctl put /coreos.com/network/config < ${BASE_DIR}/../configs/flannel-network-config.json

# start flanneld
sudo ${BASE_DIR}/../flanneld