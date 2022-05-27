#!/bin/bash

# config flannel
./etcd/etcdctl set /coreos.com/network/config < ./flannel-network-config.json

# start flanneld & checkout subnet.env
sudo ./flanneld