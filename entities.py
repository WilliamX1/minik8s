import os
import random
import re
import sys
from enum import Enum

import docker
import six
import network_utils

try:
    from docker.errors import APIError
except ImportError:
    # Fall back to <= 0.3.1 location
    from docker.client import APIError


class Container:
    def __init__(self, name, image, command, memory, cpu, port, namespace):
        self._name = name
        self._image = image
        self._command = command
        self._memory = memory
        self._cpu = cpu
        self._port = port
        self._namespace = namespace

    def name(self):
        return self._name

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

    def namespace(self):
        return self._namespace


class Status(Enum):
    STOPPED = 1
    RUNNING = 2
    KILLED = 3


class Pod:
    def __init__(self, config):
        self._suffix = config.get('suffix')
        self._name = config.get('name') + self._suffix
        self._status = Status.RUNNING
        self._volumn = config.get('volumn')
        self._containers = []
        self._namespace = None
        self._pause = None
        self._ipv4addr = None

        # set network namespace: cannot be the same as self._name
        if config.get('metadata') is None or config.get('metadata').get('namespace') is None:
            self._namespace = 'default' + self._suffix + '-namespace'
        else:
            self._namespace = config.get('metadata').get('namespace') + self._suffix + '-namespace'

        self._client = docker.from_env(version='1.25', timeout=5)

        '''
        Create a 'pause' container each pod which use a veth,
        Other containers attach to this container network, so
        they can communicate with each other using `localhost`
        '''

        self._client.networks.prune()  # delete unused networks

        # create network bridge
        print('\t==>INFO: Start Creating Network Namespace ' + self._namespace + ' ...')

        self._network = self._client.networks.create(
            name=self._namespace,
            driver="bridge",
        )

        pause_container = self._client.containers.run(image='busybox', name=self.name(),  # 这里原来是pause，防重名我改成了pod name
                                    detach=True,  # auto_remove=True,
                                    command=['sh', '-c', 'echo Hello World && sleep 3600'],
                                    network=self._network.name)
        ip_cmd = "docker network inspect --format '{{(index .Containers \"" + str(pause_container.id) +\
                 "\").IPv4Address }}' " + self._namespace
        self._ipv4addr = os.popen(ip_cmd).read()
        print('\t==>INFO: Create Network Namespace ' + self._namespace + ' successfully, IP Address: ' +
              self._ipv4addr + ' ...')

        containercfgs = config.get('containers')

        def _parse_bytes(s):
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
            return int(s[:-1]) * units[suffix]

        # 创建容器配置参数
        volumes = set()
        volumes.add(self._volumn)
        _PORT_SPEC_REGEX = re.compile(r'^(?P<p1>\d+)(?:-(?P<p2>\d+))?(?:/(?P<proto>(tcp|udp)))?$')  # noqa
        _DEFAULT_PORT_PROTOCOL = 'tcp'

        for containercfg in containercfgs:
            container = Container(containercfg['name'] + self._suffix, containercfg['image'], containercfg['command'],
                                  containercfg['resource']['memory'], containercfg['resource']['cpu'],
                                  containercfg['port'], self._namespace)
            self._containers.append(container)
            print("\t==>INFO: %s start launching...\n" % container.name())

            print(container.cpu())
            self._client.containers.run(image=container.image(), name=container.name(),  # volumes=list(volumes),
                                        cpu_shares=container.cpu(),
                                        mem_limit=_parse_bytes(container.memory()),
                                        # ports=containercfg['port'],
                                        detach=True,
                                        auto_remove=True,
                                        command=container.command(),
                                        network_mode='container:' + self.name())
            print("\t==>INFO: %s is running successfully...\n", container.name())

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
            status = self._client.api.inspect_container(container.name())
            self._client.api.start(status.get('ID', status.get('Id', None)))
        self._status = Status.RUNNING

    def stop(self):
        for container in self._containers:
            status = self._client.api.inspect_container(container.name())
            self._client.api.stop(status.get('ID', status.get('Id', None)))
        self._status = Status.STOPPED

    def kill(self):
        for container in self._containers:
            status = self._client.api.inspect_container(container.name())
            self._client.api.kill(status.get('ID', status.get('Id', None)))
        self._status = Status.KILLED

    def restart(self):
        for container in self._containers:
            status = self._client.api.inspect_container(container.name())
            self._client.api.restart(status.get('ID', status.get('Id', None)))
        self._status = Status.RUNNING

    def remove(self):
        if self._status == Status.RUNNING:
            self.stop()
        for container in self._containers:
            status = self._client.api.inspect_container(container.name())
            self._client.api.remove_container(status.get('ID', status.get('Id', None)))
        status = self._client.api.inspect_container(self._name)
        self._client.api.stop(status.get('ID', status.get('Id', None)))
        self._client.api.remove_container(status.get('ID', status.get('Id', None)))


class Service:
    def __init__(self, name, selector, port, targetport):
        self._name = name
        self._selector = selector
        self._port = port
        self._targetport = targetport
