#!/bin/bash

CURRENT_DIR=cd $(dirname $0); pwd -P

# config flannel
../etcd/etcdctl set /coreos.com/network/config < ../configs/flannel-network-config.json

# start flanneld
sudo ../flanneld