import logging
import os
import sys
from flask import Flask, request
import json
from werkzeug.utils import secure_filename
import kubeproxy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, os.path.pardir)
sys.path.append(os.path.join(BASE_DIR, '../helper'))
sys.path.append(os.path.join(BASE_DIR, '../worker'))
import utils, const, yaml_loader
import psutil
import requests
import time
import entities

isMaster = True

app = Flask(__name__)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# CORS(app, supports_credentials=True)

node_instance_name = os.popen(r"ifconfig | grep -oP 'HWaddr \K.*' | sed 's/://g' | sha256sum | awk '{print $1}'")
node_instance_name = node_instance_name.readlines()[0][:-1]
node_instance_name = node_instance_name + utils.getip()

pods = list()

init: bool = False
heart_beat_activated = False

worker_info = dict()


def get_pod_by_name(instance_name: str):
    index = -1
    pod: entities.Pod = None
    for i in range(len(pods)):
        if pods[i].instance_name == instance_name:
            index = i
            pod = pods[i]
            break
    return index, pod


@app.route('/cmd', methods=['POST'])
def execute_cmd():
    json_data = request.json
    config: dict = json.loads(json_data)
    cmd = config['cmd']
    for c in cmd:
        utils.exec_command(c, True)
    return json.dumps(dict()), 200


@app.route('/update_services/<string:behavior>', methods=['POST'])
def update_services(behavior: str):
    print("Update Service %s" % behavior)
    json_data = request.json
    config: dict = json.loads(json_data)
    service_config = config['service_config']
    pods_dict = config['pods_dict']
    global init
    if init is False:
        init = True
        kubeproxy.init_iptables()

    if behavior == 'create':
        kubeproxy.sync_service(service_config, pods_dict)
    elif behavior == 'update':
        kubeproxy.sync_service(service_config, pods_dict)
    elif behavior == 'remove':
        kubeproxy.rm_service(service_config)
    return json.dumps(service_config), 200


@app.route('/Pod', methods=['POST'])
def handle_Pod():
    config: dict = json.loads(request.json)
    print("get broadcast ", config)
    # config中不含node或者node不是自己都丢弃
    if not config.__contains__('node') or config['node'] != node_instance_name \
            or not config.__contains__('behavior'):
        return "Not found", 404
    bahavior = config['behavior']
    config.pop('behavior')
    instance_name = config['instance_name']
    if bahavior == 'create':
        print("接收到调度请求 Pod")
        # 是自己的调度，进行操作
        if config.__contains__('script_data'):
            # serverless Pod
            # todo : handle it with different worker url
            module_name = config['metadata']['labels']['module_name']
            pod_dir = os.path.join(BASE_DIR, instance_name + '/')
            print("handle serverless pod")
            if not os.path.exists(pod_dir):
                print("pod dir = ", pod_dir)
                os.mkdir(pod_dir)
            f = open(os.path.join(pod_dir, secure_filename('my_module.py')), 'w')
            f.write(config['script_data'])
            f.close()
            if config.__contains__('requirement'):
                f = open(os.path.join(pod_dir, 'requirements.txt'), 'w')
                f.write(config['requirement'])
                f.close()
            else:
                f = open(os.path.join(pod_dir, 'requirements.txt'), 'w')
                f.close()
            os.system('cp {}/worker/tmp/Dockerfile ./{}'.format(ROOT_DIR, instance_name))
            os.system('cp {}/worker/tmp/serverless_server.py ./{}'.format(ROOT_DIR, instance_name))
            os.system("cd {} && docker build . -t {}".format(instance_name, instance_name))
            config['containers'][0]['image'] = "{}:latest".format(instance_name)
        elif config.__contains__('isGPU'):
            pod_dir = os.path.join(BASE_DIR, instance_name + '/')
            print("handle gpu pod")
            if not os.path.exists(pod_dir):
                print("pod dir = ", pod_dir)
                os.mkdir(pod_dir)
            data_dir = os.path.join(pod_dir, 'data')
            if not os.path.exists(data_dir):
                os.mkdir(data_dir)
            files_list = config['files_list']
            for file_name in files_list:
                f = open(os.path.join(data_dir, file_name), 'w')
                f.write(config[file_name])
                f.close()
            os.system('cp {}/worker/gpu/Dockerfile {}/worker/{}/'.format(ROOT_DIR, ROOT_DIR, instance_name))
            os.system('cp {}/worker/gpu/gpu_server.py {}/worker/{}/'.format(ROOT_DIR, ROOT_DIR, instance_name))
            os.system('cp {}/worker/gpu/upload.sh {}/worker/{}/'.format(ROOT_DIR, ROOT_DIR, instance_name))
            os.system('cp {}/worker/gpu/download.sh {}/worker/{}/'.format(ROOT_DIR, ROOT_DIR, instance_name))
            os.system("cd {}/worker/{} && docker build . -t {}".format(ROOT_DIR, instance_name, instance_name))
            config['containers'][0]['image'] = "{}:latest".format(instance_name)
        pods.append(entities.Pod(config))
        print('{} create pod {}'.format(node_instance_name, instance_name))
        # update pod information such as ip, volume and ports
        config['status'] = 'Running'
        url = '{}/{}/{}/{}'.format(worker_info['API_SERVER_URL'], 'Pod', instance_name, 'update')
        utils.post(url=url, config=config)
        # share.set('status', str(status))
    elif bahavior == 'remove':
        print('try to delete Pod {}'.format(instance_name))
        index, pod = get_pod_by_name(instance_name)
        if index == -1:  # pod not found
            return "Not found", 404
        pods.pop(index)
        pod.stop()
        pod.remove()
    elif bahavior == 'execute':
        # todo: check the logic here
        print('try to execute Pod {} {}'.format(instance_name, config['cmd']))
        index, pod = get_pod_by_name(instance_name)
        print(pod)
        cmd = config['cmd']
        pod.exec_run(cmd)
    return "Success", 200


def init_node():
    iptable_path = os.path.dirname(os.path.realpath(__file__)) + "/sources/iptables"
    # utils.exec_command(command="echo \"127.0.0.1 localhost\" > /etc/hosts", shell=True)

    print('Default File Path is /minik8s/worker/nodes_yaml/...')
    while True:
        yaml_name = sys.argv[1] if len(sys.argv) > 1 else input('Please Enter Node Yaml File Name:')
        yaml_path = '/'.join([BASE_DIR, 'nodes_yaml', yaml_name])
        if os.path.exists(yaml_path) is False:
            logging.warning('Filepath %s Not Exists...' % yaml_path)
        else:
            restart = sys.argv[2] if len(sys.argv) > 2 else input("Restart / Init (if restart, it won't reset iptables): ")
            if restart == 'Init':
                utils.exec_command(command="iptables-restore < {}".format(iptable_path), shell=True)
                break
            elif restart == 'Restart':
                break
    nodes_info_config: dict = yaml_loader.load(yaml_path)
    logging.info(nodes_info_config)
    worker_info['IP_ADDRESS'] = nodes_info_config['IP_ADDRESS']
    worker_info['MASTER_ETCD_CLIENT_URL'] = nodes_info_config['MASTER_ETCD_CLIENT_URL']
    # write api_server_url into a file
    worker_info['API_SERVER_URL'] = nodes_info_config['API_SERVER_URL']
    f = open(const.API_SERVER_URL_PATH, 'w')
    f.write(worker_info['API_SERVER_URL'])
    f.close()

    worker_info['WORKER_PORT'] = int(nodes_info_config['WORKER_PORT'])
    cmd2 = const.FLANNEL_PATH + ' -etcd-endpoints=' + worker_info['MASTER_ETCD_CLIENT_URL']
    cmd3 = ['bash', const.DOCKER_SHELL_PATH]
    utils.exec_command(cmd2, shell=True, background=True)
    logging.warning('Please make sure flannel is running successfully, waiting for 3 seconds...')
    time.sleep(3)
    utils.exec_command(cmd3, shell=False, background=True)
    logging.warning('Please make sure docker is running successfully, waiting for 3 seconds...')
    time.sleep(3)
    # delete original iptables and restore, init for service and dns
    dir = const.DNS_CONF_PATH
    for f in os.listdir(dir):
        if f != 'default.conf':
            os.remove(os.path.join(dir, f))
    # todo: add other logic here
    global pods
    url = "{}/Node/{}".format(worker_info['API_SERVER_URL'], node_instance_name)
    r = requests.get(url)
    node_config: dict = json.loads(r.content.decode())
    if node_config.get('pod_instances'):
        for pod_instance_name in node_config['pod_instances']:
            pod_config = node_config[pod_instance_name]
            if pod_config.get('status') == 'Failed' or pod_config.get('status') == 'Succeeded':
                continue
            if pod_config.__contains__("container_names"):
                pods.append(entities.Pod(pod_config))
                print("cover pod {}".format(pod_instance_name))
    # print("node config = ", node_config)

    # todo: recover pods here

    # os.system('docker stop $(docker ps -a -q)')
    # os.system('docker rm $(docker ps -a -q)')
    data = psutil.virtual_memory()
    total = data.total  # 总内存,单位为byte
    free = data.available  # 可用内存
    memory_use_percent = (int(round(data.percent)))
    cpu_use_percent = psutil.cpu_percent(interval=1)
    # print(data, total, free, memory, cpu_use_percent)

    config: dict = {'instance_name': node_instance_name, 'kind': 'Node', 'total_memory': total,
                    'cpu_use_percent': cpu_use_percent, 'memory_use_percent': memory_use_percent,
                    'free_memory': free,
                    'ip': worker_info['IP_ADDRESS'], 'port': worker_info['WORKER_PORT'],
                    'url': ':'.join([worker_info['IP_ADDRESS'], str(worker_info['WORKER_PORT'])])}
    url = "{}/Node".format(worker_info['API_SERVER_URL'])
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)
    if r.status_code == 200:
        print("kubelet节点注册成功")
    else:
        print("kubelet节点注册失败")
        exit()


@app.route('/heartbeat', methods=['GET'])
def send_heart_beat():
    # should be activated once
    global heart_beat_activated
    if heart_beat_activated:
        return "Done!", 200
    heart_beat_activated = True
    while True:
        time.sleep(5)  # wait for 5 seconds
        data = psutil.virtual_memory()
        total = data.total  # 总内存,单位为byte
        free = data.available  # 可用内存
        memory_use_percent = (int(round(data.percent)))
        cpu_use_percent = psutil.cpu_percent(interval=None)
        config: dict = {'instance_name': node_instance_name, 'kind': 'Node', 'total_memory': total,
                        'cpu_use_percent': cpu_use_percent, 'memory_use_percent': memory_use_percent,
                        'free_memory': free, 'status': 'Running', 'pod_instances': list(),
                        'ip': worker_info['IP_ADDRESS'], 'port': worker_info['WORKER_PORT'],
                        'url': ':'.join([worker_info['IP_ADDRESS'], str(worker_info['WORKER_PORT'])])}
        containers_status = entities.get_containers_status()
        for pod in pods:
            pod_status_heartbeat = dict()
            pod_status = pod.get_status(containers_status)
            pod_status_heartbeat['instance_name'] = pod.instance_name
            pod_status_heartbeat['status'] = pod_status['status']
            pod_status_heartbeat['cpu_usage_percent'] = pod_status['cpu_usage_percent']
            pod_status_heartbeat['memory_usage_percent'] = pod_status['memory_usage_percent']
            pod_status_heartbeat['ip'] = pod_status['ip']
            pod_status_heartbeat['volume'] = pod_status['volume']
            pod_status_heartbeat['ports'] = pod_status['ports']
            pod_status_heartbeat['container_names'] = pod.container_names

            print("pod_status_heartbeat = ", pod_status_heartbeat)
            config['pod_instances'].append(pod.instance_name)
            config[pod.instance_name] = pod_status_heartbeat

        url = "{}/heartbeat".format(worker_info['API_SERVER_URL'])
        json_data = json.dumps(config)
        try:
            r = requests.post(url=url, json=json_data, timeout=1)
            if r.status_code == 200:
                print("发送心跳包成功")
            else:
                print("发送心跳包失败")
        except Exception as e:
            print("发送心跳包失败")


def main():
    init_node()
    app.run(host='0.0.0.0', port=worker_info['WORKER_PORT'], processes=True)


if __name__ == '__main__':
    main()
