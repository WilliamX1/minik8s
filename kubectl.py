import json
import re
import sys
import os
import time

import requests

import const
import kubedns
import utils

import yaml_loader
import entities
import kubeproxy


api_server_url = const.api_server_url


def print_info():
    print("version                       show minik8s version")
    print("show pods                      display extant pods")
    print("show services              display extant services")
    print("start -f filepath                  start container")
    print("start pod/service name   start stopped pod/service")
    print("stop pod/service name             stop pod/service")
    print("kill pod/service name             kill pod/service")
    print("restart pod/service name       restart pod/service")
    print("remove pod/service name         remove pod/service")


def main():
    version = '1.0.0'
    while True:
        cmd = input(">>")

        exit_match = re.fullmatch(r'exit', cmd.strip(), re.I)
        help_match = re.fullmatch(r'help', cmd.strip(), re.I)
        version_match = re.fullmatch(r'version', cmd.strip(), re.I)
        show_match = re.fullmatch(r'show *(pods|services|replicasets|dns)', cmd.strip(), re.I)
        start_file_match = re.fullmatch(r'start *-f *([a-zA-Z0-9:/\\_\-.]*yaml|yml)', cmd.strip(), re.I)
        normal_command_match = re.fullmatch(r'(start|remove) *(pod|service) *([\w-]*)', cmd.strip(), re.I)

        if exit_match:
            break
        elif help_match:
            print_info()
        elif version_match:
            print("{} v{}".format('minik8s'.title(), version))
        elif show_match:
            object_type = show_match.group(1)
            if object_type == "pods":
                r = requests.get(url='{}/Pod'.format(api_server_url))
                pods_dict = json.loads(r.content.decode('UTF-8'))
                print("{0:100}{1:30}{2:30}".format('name', 'status', 'created time'))
                for pod_instance_name in pods_dict['pods_list']:
                    pod_config = pods_dict[pod_instance_name]
                    created_time = int(time.time() - pod_config['created_time'])
                    created_time = str(created_time // 60) + "m" + str(created_time % 60) + 's'
                    print(f"{pod_instance_name:100}{pod_config['status']:30}{created_time.strip():30}")
            elif object_type == "services":
                service_dict = utils.get_service_dict(api_server_url=api_server_url)
                kubeproxy.get_services(service_dict)
            elif object_type == 'replicasets':
                r = requests.get(url='{}/ReplicaSet'.format(api_server_url))
                rc_dict = json.loads(r.content.decode('UTF-8'))
                print("{0:100}{1:30}{2:30}{3:15}".format('name', 'status', 'created time', 'replicas'))
                for rc_instance_name in rc_dict['replica_sets_list']:
                    rc_config = rc_dict[rc_instance_name]
                    rc_status = 'TO DO'  # todo
                    created_time = int(time.time() - rc_config['created_time'])
                    created_time = str(created_time // 60) + "m" + str(created_time % 60) + 's'
                    replicas = str(rc_config['spec']['replicas']).strip()
                    print(f"{rc_instance_name:100}{rc_status:30}{created_time.strip():30}{replicas:15}")
            elif object_type == 'dns':
                dns_dict = utils.get_dns_dict(api_server_url=api_server_url)
                kubedns.get_dns(dns_dict)
            else:
                # todo : handle other types
                pass
        elif normal_command_match:
            pass
            cmd_type = normal_command_match.group(1)  # start or remove
            object_type = normal_command_match.group(2)  # pod or service
            instance_name = normal_command_match.group(3)  # instance_name
            if object_type == 'pod':
                json_data = json.dumps(dict())
                r = requests.post(url='{}/Pod/{}/{}'.format(api_server_url, instance_name, cmd_type), json=json_data)

            if object_type == 'service':
                if cmd_type == 'remove':
                    service_dict = utils.get_service_dict(api_server_url=api_server_url)
                    if instance_name not in service_dict['services_list']:
                        print("Service {} Not Found".format(instance_name))
                    else:
                        url = "{}/Service/{}/{}".format(api_server_url, instance_name, 'remove')
                        config = service_dict[instance_name]
                        utils.post(url=url, config=config)
            #     raise NotImplementedError
            # elif object_type == 'pod':
            #     pod = pods[object_name]
            #     getattr(pod, cmd_type)()
        elif start_file_match:
            pass
            # file_path = start_file_match.group(1)
            # if not os.path.isfile(file_path):
            #     print("file not exist")
            #     continue
            # config = yaml_loader.load(file_path)
            # if 'name' not in config:
            #     sys.stdout.write('yaml name is missing')
            # if config.get('kind') == 'pod':
            #     name = config.get('name')
            #     检查pod是否已存在
            # if name in pods:
            #     print("pod:{} already exist".format(name))
            #     continue
            # 创建pod并创建开启容器
            # pod = entities.Pod(config)
            # pods[name] = pod
            # print('pod:{} created successfully'.format(name))
            # elif config.get('kind') == 'service':
            # 创建service（检查重名）
            # print('test')
            # else:
            #     print("file content error")

        else:
            print("Command does not match any valid command. Try 'help' for more information. ")


if __name__ == '__main__':
    main()
