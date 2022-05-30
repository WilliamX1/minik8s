#!/bin/bash

cat /run/flannel/subnet.env

# create docker parameters & checkout docker_opts.env
sudo systemctl stop docker.socket
sudo systemctl stop docker
source /run/flannel/subnet.env
sudo ifconfig docker0 ${FLANNEL_SUBNET}
sudo dockerd --bip=${FLANNEL_SUBNET} --mtu=${FLANNEL_MTU}