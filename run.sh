#!/bin/bash

# python3 master/etcd_controller.py &
# etcd_controller_id=$!
# sleep 10s
python3 master/api_server.py &
api_server_id=$!
sleep 1s
python3 master/node_controller.py &
node_controller_id=$!
sleep 1s
python3 master/garbage_collector.py &
garbage_collector_id=$!
sleep 1s
python3 master/replica_set_controller.py &
replica_set_controller_id=$!
sleep 1s
python3 master/service_controller.py &
service_controller_id=$!
sleep 1s
python3 master/dns_controller.py &
dns_controller_id=$!
sleep 1s
python3 worker/kubelet_flask.py worker1.yaml Init &
kubelet_flask_id=$!
sleep 4s

kill -9 $kubelet_flask_id
kill -9 $dns_controller_id
kill -9 $service_controller_id
kill -9 $replica_set_controller_id
kill -9 $garbage_collector_id
kill -9 $node_controller_id
kill -9 $api_server_id
# kill -9 $etcd_controller_id
