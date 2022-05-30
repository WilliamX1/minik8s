#!/bin/bash

# config flannel
./etcd/etcdctl set /coreos.com/network/config < ./configs/flannel-network-config.json

# start flanneld
sudo ./flanneld