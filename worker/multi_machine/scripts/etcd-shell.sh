#!/bin/bash

BASE_DIR=$(cd $(dirname $0); pwd)
# bash etcd-shell.sh etcd0 http://10.119.11.120 etcd0=http://10.119.11.120:2380 new
# bash etcd-shell.sh etcd1 http//10.119.10.16 etcd1=http://10.119.10.16:2380,etcd0=http://10.119.11.120:2380 existing
# ...

ETCD_NAME=$1  # etcd name: such as etcd0
IP_ADDRESS=$2  # etcd local ip address: such as http://10.119.11.120
ETCD_INITIAL_CLUSTER=$3  # etcd0=http://10.119.11.120:2380,etcd1=http://10.119.10.16:2380
ETCD_INITIAL_CLUSTER_STATE=$4  # new/existing

${BASE_DIR}/../etcd/etcd \
  -name ${ETCD_NAME} \
  -advertise-client-urls ${IP_ADDRESS}:2379 \
  -listen-client-urls http://0.0.0.0:2379 \
  -initial-advertise-peer-urls ${IP_ADDRESS}:2380 \
  -listen-peer-urls http://0.0.0.0:2380 \
  -initial-cluster-token etcd-cluster \
  -initial-cluster ${ETCD_INITIAL_CLUSTER} \
  -initial-cluster-state ${ETCD_INITIAL_CLUSTER_STATE}


# config flannel
# ${BASE_DIR}/../etcd/etcdctl put /coreos.com/network/config < ${BASE_DIR}/../configs/flannel-network-config.json
