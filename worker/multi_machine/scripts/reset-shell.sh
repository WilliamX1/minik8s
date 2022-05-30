#!/bin/bash

# reset docker0 ip address to 172.17.0.1
sudo systemctl stop docker.socket
sudo systemctl stop docker
sudo ifconfig docker0 172.17.0.1
sudo dockerd --bip=172.17.0.1/16 --mtu=1500