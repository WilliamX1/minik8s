import os
import random
import re
import sys
from enum import Enum

import docker
import iptc
import six
import kubeproxy

try:
    from docker.errors import APIError
except ImportError:
    # Fall back to <= 0.3.1 location
    from docker.client import APIError

class Container:
    def __init__(self, name, suffix, image, command, memory, cpu, port):
        self._name = name
        self._suffix = suffix
        self._image = image
        self._command = command
        self._memory = memory
        self._cpu = cpu
        self._port = port

    def name(self):
        return self._name

    def suffix(self):
        return self._suffix

    def image(self):
        return self._image

    def command(self):
        return self._command

    def memory(self):
        return self._memory

    def cpu(self):
        return self._cpu

    def port(self):
        return self._port

    def set_cpu(self, cpu):
        self._cpu = cpu

    def set_memory(self, memory):
        self._memory = memory


class Status(Enum):
    STOPPED = 1
    RUNNING = 2
    KILLED = 3


def parse_bytes(s):
    if not s or not isinstance(s, six.string_types):
        return s
    units = {'k': 1024,
             'm': 1024 * 1024,
             'g': 1024 * 1024 * 1024}
    suffix = s[-1].lower()
    if suffix not in units.keys():
        if not s.isdigit():
            sys.stdout.write('Unknown unit suffix {} in {}!'
                             .format(suffix, s))
            return 0
        return int(s)
    return int(float(s[:-1]) * units[suffix])


class Pod:
    def __init__(self, config):
        self.config = config
        self.instance_name = config.get('instance_name')
        self._name = config.get('name')
        self._status = Status.RUNNING
        self._volumn = config.get('volumn')
        self._containers = []
        self._pause = None
        self._mem = config.get('mem')
        self._cpu = {}
        self._ipv4addr = None
        self._cpu_num = config.get('cpu')
        #            containername:'0,1,2'

        self._client = docker.from_env(version='1.25', timeout=5)

        '''
                Create a 'pause' container each pod which use a veth,
                Other containers attach to this container network, so
                they can communicate with each other using `localhost`
        '''
        pause_container = self._client.containers.run(image='kubernetes/pause', name=self.instance_name,
                                                      detach=True, auto_remove=True,
                                                      network_mode="bridge")

        ip_cmd = "docker inspect --format '{{ .NetworkSettings.IPAddress }}' %s" % pause_container.name
        self._ipv4addr = os.popen(ip_cmd).read()
        print('\t==>INFO: Pod %s IP Address: %s ...' % (self.instance_name, self._ipv4addr))

        containercfgs = config.get('containers')

        # 创建容器配置参数
        volumes = set()
        volumes.add(self._volumn)
        for containercfg in containercfgs:
            container = Container(containercfg['name'], self.instance_name, containercfg['image'],
                                  containercfg['command'],
                                  containercfg['resource']['memory'], containercfg['resource']['cpu'],
                                  containercfg['port'])
            self._cpu[containercfg['name']] = containercfg['resource']['cpu']
            self._containers.append(container)
            print(pause_container.name)
            self._client.containers.run(image=container.image(), name=container.name() + container.suffix(),
                                        volumes=list(volumes),
                                        # cpuset_cpus=container.cpu(),
                                        mem_limit=parse_bytes(container.memory()),
                                        detach=True,
                                        # auto_remove=True,
                                        command=container.command(),
                                        network_mode='container:' + pause_container.name)

    def name(self):
        return self._name

    def status(self):
        return self._status

    def volumn(self):
        return self._volumn

    def contains(self):
        return self._containers

    def client(self):
        return self._client

    def append(self, container):
        self._containers.append(container)

    def start(self):
        for container in self._containers:
            name = container.name() + container.suffix()
            status = self._client.api.inspect_container(name)
            self._client.api.start(status.get('ID', status.get('Id', None)))
        self._status = Status.RUNNING

    def stop(self):
        for container in self._containers:
            name = container.name() + container.suffix()
            status = self._client.api.inspect_container(name)
            self._client.api.stop(status.get('ID', status.get('Id', None)))
        self._status = Status.STOPPED

    def kill(self):
        for container in self._containers:
            name = container.name() + container.suffix()
            status = self._client.api.inspect_container(name)
            self._client.api.kill(status.get('ID', status.get('Id', None)))
        self._status = Status.KILLED

    def restart(self):
        for container in self._containers:
            name = container.name() + container.suffix()
            status = self._client.api.inspect_container(name)
            self._client.api.restart(status.get('ID', status.get('Id', None)))
        self._status = Status.RUNNING

    def remove(self):
        if self._status == Status.RUNNING:
            self.stop()
        for container in self._containers:
            name = container.name() + container.suffix()
            status = self._client.api.inspect_container(name)
            self._client.api.remove_container(status.get('ID', status.get('Id', None)))
        name = self.instance_name
        status = self._client.api.inspect_container(name)
        self._client.api.stop(status.get('ID', status.get('Id', None)))
        self._client.api.remove_container(status.get('ID', status.get('Id', None)))

    def get_status(self):
        pod_status = {'memory_usage_percent': 0, 'cpu_usage_percent': 0, 'status': 'Running'}
        successfully_exit_number = 0
        error_exit_number = 0
        missing_container = 0
        for container in self._containers:
            name = container.name() + container.suffix()
            tmp = os.popen('docker stats --no-stream | grep {}'.format(name)).readlines()
            if not tmp or len(tmp) < 1:
                print("container not found")
                missing_container += 1
                break
            parameter = tmp[0].split()
            # container ID | container Name | CPU USAGE | MEM USAGE | / | MEM LIMIT | MEM PERCENT | NET IO | BLOCK IO | PIDS
            pod_status['cpu_usage_percent'] += float(parameter[2][:-1])
            pod_status['memory_usage_percent'] += float(parameter[6][:-1])
            a = self._client.api.inspect_container(name)
            filter_dict = dict()
            filter_dict['id'] = a.get('ID', a.get('Id', None))
            container_stats = self._client.api.containers(filters=filter_dict)[0]
            state = container_stats['State']
            status = container_stats['Status'].split()
            if status[0] == 'Up':
                pass
            elif status[0] == 'Exited':
                exit_code = int(status[1][1:-1])
                if exit_code == 0:
                    successfully_exit_number += 1
                else:
                    error_exit_number += 1
        # k8s Pod状态详解 https://blog.csdn.net/weixin_42516922/article/details/123007149
        if missing_container != 0:
            pod_status['status'] = 'Failed'
        elif successfully_exit_number == len(self._containers):
            pod_status['status'] = 'Succeeded'
        elif (successfully_exit_number + error_exit_number) == len(self._containers) and error_exit_number > 0:
            pod_status['status'] = 'Failed'
        return pod_status
