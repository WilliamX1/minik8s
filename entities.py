import re
import sys
from enum import Enum

import docker
import six

try:
    from docker.errors import APIError
except ImportError:
    # Fall back to <= 0.3.1 location
    from docker.client import APIError


class Container:
    def __init__(self, name, image, command, memory, cpu, port, network):
        self._name = name
        self._image = image
        self._command = command
        self._memory = memory
        self._cpu = cpu
        self._port = port
        self._network = network

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

    def network(self):
        return self._network


class Status(Enum):
    STOPPED = 1
    RUNNING = 2
    KILLED = 3


class Pod:
    def __init__(self, config):
        self._name = config.get('name')
        self._status = Status.RUNNING
        self._volumn = config.get('volumn')
        self._containers = []

        containercfgs = config.get('containers')
        i = 0
        # 创建容器配置参数
        volumes = set()
        volumes.add(self._volumn)
        _PORT_SPEC_REGEX = re.compile(r'^(?P<p1>\d+)(?:-(?P<p2>\d+))?(?:/(?P<proto>(tcp|udp)))?$')  # noqa
        _DEFAULT_PORT_PROTOCOL = 'tcp'
        backend_url = '{:s}://{:s}:{:d}'.format(
            "http", "localhost", 2375)
        backend = docker.DockerClient(
            base_url=backend_url,
            version=str(1.21),
            timeout=5)
        networkname = "zookeeper-net"
        backend.networks.create(networkname, driver="bridge")
        self._backend = backend

        def _parse_ports(ports):
            """Parse port mapping specifications for this container."""

            def parse_port_spec(spec):
                if type(spec) == int:
                    spec = str(spec)

                m = _PORT_SPEC_REGEX.match(spec)
                if not m:
                    sys.stdout.write(('Invalid port specification {}! '
                                      'Expected format is <port>, <p1>-<p2> '
                                      'or <port>/{{tcp,udp}}.').format(spec))
                    return {}
                s = m.group('p1')
                if m.group('p2'):
                    s += '-' + m.group('p2')
                proto = m.group('proto') or _DEFAULT_PORT_PROTOCOL
                s += '/' + proto
                return s

            result = {}
            '''
            BUG: Need Fix Transfer Function
            '''
            for name, spec in ports.items():
                # Single number, interpreted as being a TCP port number and to be
                # the same for the exposed port and external port bound on all
                # interfaces.
                '''
                if type(spec) == int:
                    result[name] = {
                        'exposed': parse_port_spec(spec),
                        'external': ('0.0.0.0', parse_port_spec(spec)),
                    }
                '''
                if type(spec) == int:
                    result[name] = spec

                # Port spec is a string. This means either a protocol was specified
                # with /tcp or /udp, that a port range was specified, or that a
                # mapping was provided, with each side of the mapping optionally
                # specifying the protocol.
                # External port is assumed to be bound on all interfaces as well.
                elif type(spec) == str:
                    parts = list(map(parse_port_spec, spec.split(':')))
                    if len(parts) == 1:
                        # If only one port number is provided, assumed external =
                        # exposed.
                        parts.append(parts[0])
                    elif len(parts) > 2:
                        sys.stdout.write(('Invalid port spec {} for port {} of {}! ' +
                                          'Format should be "name: external:exposed".').format(
                            spec, name))
                        return {}

                    if parts[0][-4:] != parts[1][-4:]:
                        sys.stdout.write('Mismatched protocols between {} and {}!'.format(
                            parts[0], parts[1]))
                        return {}

                    result[name] = {
                        'exposed': parts[0],
                        'external': ('0.0.0.0', parts[1]),
                    }

                # Port spec is fully specified.
                elif type(spec) == dict and \
                        'exposed' in spec and 'external' in spec:
                    spec['exposed'] = parse_port_spec(spec['exposed'])

                    if type(spec['external']) != list:
                        spec['external'] = ('0.0.0.0', spec['external'])
                    spec['external'] = (spec['external'][0],
                                        parse_port_spec(spec['external'][1]))

                    result[name] = spec

                else:
                    sys.stdout.write('Invalid port spec {} for port {} of {}!'.format(
                        spec, name))
                    return {}

            # print result
            '''
            for key, value in result.items():
                print(key)
                print(value)
            return result
            '''

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

        for containercfg in containercfgs:
            container = Container(self._name + '-{}'.format(i), containercfg['image'], containercfg['command'],
                                  containercfg['resource']['memory'], containercfg['resource']['cpu'],
                                  containercfg['port'], networkname)
            self._containers.append(container)
            i += 1

            '''
            host_config = backend.create_host_config(mem_limit=_parse_bytes(container.memory()))
            backend.create_container(image=container.image(), name=container.name(), volumes=list(volumes),
                                     cpu_shares=container.cpu(), host_config=host_config,
                                     ports=_parse_ports(containercfg['port']), detach=True, command=container.command())
            '''
            backend.containers.run(image=container.image(), name=container.name(), volumes=list(volumes),
                                   cpu_shares=container.cpu(), mem_limit=_parse_bytes(container.memory()),
                                   ports=_parse_ports(containercfg['port']), detach=True, command=container.command(),
                                   network=networkname)

            '''
            status = backend.inspect_container(container.name())
            backend.start(status.get('ID', status.get('Id', None)))
            '''

    def name(self):
        return self._name

    def status(self):
        return self._status

    def volumn(self):
        return self._volumn

    def contains(self):
        return self._containers

    def backend(self):
        return self._backend

    def append(self, container):
        self._containers.append(container)

    def start(self):
        for container in self._containers:
            status = self._backend.inspect_container(container.name())
            self._backend.start(status.get('ID', status.get('Id', None)))
        self._status = Status.RUNNING

    def stop(self):
        for container in self._containers:
            status = self._backend.inspect_container(container.name())
            self._backend.stop(status.get('ID', status.get('Id', None)))
        self._status = Status.STOPPED

    def kill(self):
        for container in self._containers:
            status = self._backend.inspect_container(container.name())
            self._backend.kill(status.get('ID', status.get('Id', None)))
        self._status = Status.KILLED

    def restart(self):
        for container in self._containers:
            status = self._backend.inspect_container(container.name())
            self._backend.restart(status.get('ID', status.get('Id', None)))
        self._status = Status.RUNNING

    def remove(self):
        for container in self._containers:
            status = self._backend.inspect_container(container.name())
            self._backend.remove_container(status.get('ID', status.get('Id', None)))


class Service:
    def __init__(self, name, selector, port, targetport):
        self._name = name
        self._selector = selector
        self._port = port
        self._targetport = targetport
