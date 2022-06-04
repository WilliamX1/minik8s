import logging
import os
import sys
from enum import Enum

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
import const, utils

import docker
import six

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

try:
    from docker.errors import APIError
except ImportError:
    # Fall back to <= 0.3.1 location
    from docker.client import APIError


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
        if config.get('container_names') is None:
            restart = False
        else:
            restart = True
        if not restart:  # for first create Pod
            self.instance_name = config.get('instance_name')
            self.volume = config.get('volume')
            # if volume start with $PWD, change it to cur absolute path: /xx/xx/minik8s/
            if self.volume is None:
                self.volume = list()
            self.volume = [v.replace("$", const.ROOT_DIR) for v in self.volume]
            self.ports = list()
            self.container_names = list()
            self.client = docker.from_env(version='1.25', timeout=5)

            '''
            Create a 'pause' container each pod which use a veth,
            Other containers attach to this container network, so
            they can communicate with each other using `localhost`
            '''

            pause_container = self.client.containers.run(image='kubernetes/pause', name=self.instance_name,
                                                         detach=True, auto_remove=True,
                                                         network_mode="bridge")
            self.container_names.append(self.instance_name)

            ip_cmd = "docker inspect --format '{{ .NetworkSettings.IPAddress }}' %s" % pause_container.name
            self.ipv4addr = os.popen(ip_cmd).read().strip()
            containercfgs = config.get('containers')

            # 创建容器配置参数
            for containercfg in containercfgs:
                container_name = containercfg['name'] + self.instance_name
                self.container_names.append(container_name)
                cpu_string = "0-{}".format(containercfg['resource']['cpu'])
                container = self.client.containers.run(image=containercfg['image'], name=container_name,
                                                       volumes=self.volume,
                                                       cpuset_cpus=cpu_string,
                                                       mem_limit=parse_bytes(containercfg['resource']['memory']),
                                                       detach=True,
                                                       # auto_remove=True,
                                                       command=containercfg['command'],
                                                       network_mode='container:' + pause_container.name)
                if containercfg.get('port') and containercfg['port'] != '':
                    self.ports.append(str(containercfg['port']))
                logging.info("\tcontainer %s run successfully" % container.name)
            logging.info('Pod %s run successfully ...' % self.instance_name)
            config['ip'] = self.ipv4addr
            config['volume'] = self.volume
            config['ports'] = self.ports if len(self.ports) > 0 else '[]'
        else:  # after kubelet crash, we need to recover the structure
            self.instance_name = config['instance_name']
            self.container_names = config['container_names']
            self.ipv4addr = config['ip']
            self.volume = config.get('volume')
            # if volume start with $PWD, change it to cur absolute path: /xx/xx/minik8s/
            if self.volume is None:
                self.volume = list()
            self.volume = [v.replace("$", const.ROOT_DIR) for v in self.volume]
            self.ports = list()
            containercfgs = config.get('containers')
            # 创建容器配置参数
            for containercfg in containercfgs:
                if containercfg.get('port') and containercfg['port'] != '':
                    self.ports.append(str(containercfg['port']))

    def start(self):
        for container_name in self.container_names:
            status = self.client.api.inspect_container(container_name)
            self.client.api.start(status.get('ID', status.get('Id', None)))

    def stop(self):
        for container_name in self.container_names:
            status = self.client.api.inspect_container(container_name)
            self.client.api.stop(status.get('ID', status.get('Id', None)))

    def kill(self):
        for container_name in self.container_names:
            status = self.client.api.inspect_container(container_name)
            self.client.api.kill(status.get('ID', status.get('Id', None)))

    def restart(self):
        for container_name in self.container_names:
            status = self.client.api.inspect_container(container_name)
            self.client.api.restart(status.get('ID', status.get('Id', None)))

    def remove(self):
        for container_name in self.container_names:
            status = self.client.api.inspect_container(container_name)
            self.client.api.remove_container(status.get('ID', status.get('Id', None)))

    def get_status(self, containers_status: dict):
        pod_status = {'memory_usage_percent': 0, 'cpu_usage_percent': 0, 'status': 'Running'}
        successfully_exit_number = 0
        error_exit_number = 0
        missing_container = 0
        for container_name in self.container_names:
            print("container_name = ", container_name)
            container_status = containers_status.get(container_name)
            if container_status is None:
                missing_container += 1
                print("missing container_name = ", container_name)
                continue
            pod_status['cpu_usage_percent'] += container_status['cpu_usage_percent']
            pod_status['memory_usage_percent'] += container_status['memory_usage_percent']
            status = container_status['status']
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
        elif successfully_exit_number == len(self.container_names):
            pod_status['status'] = 'Succeeded'
        elif (successfully_exit_number + error_exit_number) == len(self.container_names) and error_exit_number > 0:
            pod_status['status'] = 'Failed'
        # Get Ipv4 Address
        pod_status['ip'] = self.ipv4addr
        pod_status['volume'] = self.volume
        pod_status['ports'] = self.ports
        return pod_status

    def exec_run(self, cmd, container_name=None):
        """
        run a command inside a container. Similar to `docker exec`
        :param cmd: command
        :param container_name: None means all
        :return:
        """
        for name in self.container_names:
            if name == self.instance_name:  # pause container will not exec
                continue
            if container_name is None or container_name == name:
                ct = self.client.containers.get(name)
                print('**********************')
                print(cmd)
                for c in cmd:
                    # TO DO
                    print('++++++++++++++'
                          '-------------')
                    print(ct.id)
                    print(c)
                    utils.exec_command('docker exec {} bash -c "{}"'.format(ct.id, c), shell=True)
                    # ct.exec_run(cmd=c)


def get_containers_status():
    container_status_list = dict()
    tmp = os.popen('docker stats --no-stream').readlines()
    for i in range(1, len(tmp)):
        try:
            parameter = tmp[i].split()
            container_status = dict()
            container_status['id'] = parameter[0]
            container_status['name'] = parameter[1]
            container_status['cpu_usage_percent'] = float(parameter[2][:-1])
            container_status['memory_usage_percent'] = float(parameter[6][:-1])

            client = docker.from_env(version='1.25', timeout=5)

            a = client.api.inspect_container(container_status['id'])
            filter_dict = dict()
            filter_dict['id'] = a.get('ID', a.get('Id', None))
            container_stats = client.api.containers(filters=filter_dict)[0]
            state = container_stats['State']
            status = container_stats['Status'].split()
            container_status['status'] = status
            container_status_list[container_status['name']] = container_status
        except Exception as e:
            pass
    return container_status_list