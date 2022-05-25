#!/bin/bash
sudo ./etcd/etcd \
  -name etcd0 \
  -advertise-client-urls http://10.119.11.120:2379,http://10.119.11.120:4001 \
  -listen-client-urls http://0.0.0.0:2379,http://0.0.0.0:4001 \
  -initial-advertise-peer-urls http://10.119.11.120:2380 \
  -listen-peer-urls http://0.0.0.0:2380 \
  -initial-cluster-token etcd-cluster \
  -initial-cluster etcd0=http://10.119.11.120:2380,etcd1=http://10.119.10.16:2380 \
  -initial-cluster-state new



