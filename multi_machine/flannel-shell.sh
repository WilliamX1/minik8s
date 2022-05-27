#!/bin/bash

# config flannel
./etcd/etcdctl set /coreos.com/network.config < ./flannel-network-config.json

# start flanneld & checkout subnet.env
# ETCD_INITIAL_CLUSTER=$0  #  "http://10.119.10.16:2379,http://10.119.11.120:2379"
nohup ./flanneld  #  --etcd-endpoints=ETCD_INITIAL_CLUSTER &
cat /run/flannel/subnet.env

# create docker parameters & checkout docker_opts.env
./mk-docker-opts.sh -d /run/docker_opts.env -c
cat /run/docker_opts.env

# restart docker
systemctl daemon-reload
systemctl restart docker