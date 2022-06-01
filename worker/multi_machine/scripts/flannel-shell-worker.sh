#!/bin/bash

BASE_DIR=$(cd $(dirname $0); pwd)
ETCD_ENDPOINTS=$1

# start flanneld
sudo ${BASE_DIR}/../flanneld -etcd-endpoints=ETCD_ENDPOINTS