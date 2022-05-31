#!/bin/bash

# clean up residual processes

ps aux | grep python3 | awk '{print $2}' | xargs kill -9
ps aux | grep etcd | awk '{print $2}' | xargs kill -9
ps aux | grep flannel | awk '{print $2}' | xargs kill -9
ps aux | grep docker | awk '{print $2}' | xargs kill -9