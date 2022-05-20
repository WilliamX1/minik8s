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

per_cpu_size = 2.2 * 1024 * 1024 * 1024


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
    def __init__(self, config, restart):
        self._suffix = config.get('suffix')
        self._name = config.get('name')
        self._status = Status.RUNNING
        self._volumn = config.get('volumn')
        self._containers = []
        self._pause = None
        self._mem = config.get('mem')
        self._cpu = {}
        self._ipv4addr = None
        #            containername:'0,1,2'

        self._client = docker.from_env(version='1.25', timeout=5)

        if restart:
            containercfgs = config.get('containers')
            for containercfg in containercfgs:
                container = Container(containercfg['name'], self._suffix, containercfg['image'],
                                      containercfg['command'],
                                      containercfg['resource']['memory'], containercfg['resource']['cpu'],
                                      containercfg['port'])
                self._containers.append(container)
            if config.get('status') == 'Status.RUNNING':
                self._status = Status.RUNNING
            elif config.get('status') == 'Status.STOPPED':
                self._status = Status.STOPPED
            elif config.get('status') == 'Status.KILLED':
                self._status = Status.KILLED
            # print('\t==>INFO: pod {} reconnect'.format(self._name + self._suffix))
        else:
            '''
                    Create a 'pause' container each pod which use a veth,
                    Other containers attach to this container network, so
                    they can communicate with each other using `localhost`
                    '''
            pause_container = self._client.containers.run(image='kubernetes/pause', name=self._name + self._suffix,
                                                          detach=True, auto_remove=True,
                                                          network_mode="bridge")

            ip_cmd = "docker inspect --format '{{ .NetworkSettings.IPAddress }}' %s" % pause_container.name
            self._ipv4addr = os.popen(ip_cmd).read()
            print('\t==>INFO: Pod %s IP Address: %s ...' % (self._name, self._ipv4addr))

            containercfgs = config.get('containers')

            # 创建容器配置参数
            volumes = set()
            volumes.add(self._volumn)
            for containercfg in containercfgs:
                container = Container(containercfg['name'], self._suffix, containercfg['image'],
                                      containercfg['command'],
                                      containercfg['resource']['memory'], containercfg['resource']['cpu'],
                                      containercfg['port'])
                self._cpu[containercfg['name']] = containercfg['resource']['cpu']
                self._containers.append(container)
                print(pause_container.name)
                self._client.containers.run(image=container.image(), name=container.name() + container.suffix(),
                                            volumes=list(volumes),
                                            cpuset_cpus=container.cpu(),
                                            mem_limit=parse_bytes(container.memory()),
                                            detach=True,
                                            # auto_remove=True,
                                            command=container.command(),
                                            network_mode='container:' + pause_container.name)

    def name(self):
        return self._name

    def suffix(self):
        return self._suffix

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
        name = self._name + self._suffix
        status = self._client.api.inspect_container(name)
        self._client.api.stop(status.get('ID', status.get('Id', None)))
        self._client.api.remove_container(status.get('ID', status.get('Id', None)))

    def resource_status(self):
        s = {'total_mem': self._mem, 'mem': 0,
             'cpu': {'0': 0, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '7': 0, '8': 0, '9': 0, '10': 0, '11': 0}}

        for container in self._containers:
            name = container.name() + container.suffix()
            status = self._client.api.inspect_container(name)
            s['mem'] += \
            self._client.containers.get(status.get('ID', status.get('Id', None))).stats(stream=False)['memory_stats'][
                'usage']
            percpu_usage = \
            self._client.containers.get(status.get('ID', status.get('Id', None))).stats(stream=False)['cpu_stats'][
                'cpu_usage']['percpu_usage']
            for i in range(0, 12):
                s['cpu'][str(i)] += percpu_usage[i] / per_cpu_size
        s['mem'] = s['mem'] / parse_bytes(s['total_mem'])
        return s

    def scale(self, the_scale_config):
        index = 0
        for new_container_scale in the_scale_config['containers']:
            while self._containers[index].name() != new_container_scale['name']:
                index += 1
            new_cpu = new_container_scale['resource'].get('cpu', 0)
            if new_cpu != 0:
                self._containers[index].set_cpu(new_container_scale['resource']['cpu'])
            new_memory = new_container_scale['resource'].get('memory', '0g')
            if new_memory != '0g':
                self._containers[index].set_memory(new_container_scale['resource']['memory'])
            # 修改实际容器


class Service:
    def __init__(self, config):
        self._name = config.get("name")
        self._selector = config.get("selector")
        self._ports = config.get("ports")  # include port and targetPort



