import logging
import re
import time

from userland import kubedns
import sys, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
import utils, const

from worker import kubeproxy
import prettytable


api_server_url = const.api_server_url


def print_info():
    print("version                              show minik8s version")
    print("start -f filepath                    start container")
    print("start pod name                       start stopped pod")
    print("stop pod name                        stop pod/service")
    print("kill pod name                        kill pod/service")
    print("show pods/services/dns               display extant pods/services/dns")
    print("update service/dns name              update service/dns")
    print("restart pod/service/dns name         restart pod/service/dns")
    print("remove pod/service/dns name          remove pod/service/dns")


def main():
    version = '1.0.0'
    while True:
        cmd = input(">>")

        exit_match = re.fullmatch(r'exit', cmd.strip(), re.I)
        help_match = re.fullmatch(r'help', cmd.strip(), re.I)
        version_match = re.fullmatch(r'version', cmd.strip(), re.I)
        show_match = re.fullmatch(r'show *(pods|services|replicasets|dns)', cmd.strip(), re.I)
        start_file_match = re.fullmatch(r'start *-f *([a-zA-Z0-9:/\\_\-.]*yaml|yml)', cmd.strip(), re.I)
        pod_command_match = re.fullmatch(r'(start|remove) * pod *([\w-]*)', cmd.strip(), re.I)
        service_command_match = re.fullmatch(r'(update|restart|remove) * service *([\w-]*)', cmd.strip(), re.I)
        dns_command_match = re.fullmatch(r'(update|restart|remove) * dns *([\w-]*)', cmd.strip(), re.I)
        curl_match = re.fullmatch(r'curl * ([a-zA-Z0-9:/\\_\-.]*)', cmd.strip(), re.I)  # only used for test

        if exit_match:
            break
        elif help_match:
            print_info()
        elif version_match:
            print("{} v{}".format('minik8s'.title(), version))
        elif show_match:
            object_type = show_match.group(1)
            if object_type == "pods":
                pods_dict = utils.get_pod_dict(api_server_url=api_server_url)
                tb = prettytable.PrettyTable()
                tb.field_names = ['name', 'status', 'created time']
                for pod_instance_name in pods_dict['pods_list']:
                    pod_config = pods_dict[pod_instance_name]
                    created_time = int(time.time() - pod_config['created_time'])
                    created_time = str(created_time // 60) + "m" + str(created_time % 60) + 's'
                    tb.add_row([pod_instance_name, pod_config['status'], created_time.strip()])
                print(tb)
            elif object_type == "services":
                service_dict = utils.get_service_dict(api_server_url=api_server_url)
                kubeproxy.show_services(service_dict)
            elif object_type == 'replicasets':
                rc_dict = utils.get_replicaset_dict(api_server_url=api_server_url)
                tb = prettytable.PrettyTable()
                tb.field_names = ['name', 'status', 'created time', 'replicas']
                for rc_instance_name in rc_dict['replica_sets_list']:
                    rc_config = rc_dict[rc_instance_name]
                    rc_status = 'TO DO'  # todo
                    created_time = int(time.time() - rc_config['created_time'])
                    created_time = str(created_time // 60) + "m" + str(created_time % 60) + 's'
                    replicas = str(rc_config['spec']['replicas']).strip()
                    tb.add_row([rc_instance_name, rc_status, created_time.strip(), replicas])
                print(tb)
            elif object_type == 'dns':
                dns_dict = utils.get_dns_dict(api_server_url=api_server_url)
                kubedns.show_dns(dns_dict)
            else:
                # todo : handle other types
                pass
        elif pod_command_match:
            pass
            '''cmd_type = pod_command_match.group(1)  # start or remove
            instance_name = pod_command_match.group(2)  # instance_name
            json_data = json.dumps(dict())
            r = requests.post(url='{}/Pod/{}/{}'.format(api_server_url, instance_name, cmd_type), json=json_data)
            '''
            #     raise NotImplementedError
            # elif object_type == 'pod':
            #     pod = pods[object_name]
            #     getattr(pod, cmd_type)()
        elif service_command_match:
            cmd_type = service_command_match.group(1)  # restart or update or remove
            instance_name = service_command_match.group(2)  # instance_name
            service_dict = utils.get_service_dict(api_server_url=api_server_url)
            if instance_name not in service_dict['services_list']:
                logging.warning("Service {} Not Found".format(instance_name))
            else:
                url = "{}/Service/{}/{}".format(api_server_url, instance_name, cmd_type)
                config = service_dict[instance_name]
                utils.post(url=url, config=config)
        elif dns_command_match:
            cmd_type = dns_command_match.group(1)  # restart or update or remove
            instance_name = dns_command_match.group(2)  # instance_name
            dns_dict = utils.get_dns_dict(api_server_url=api_server_url)
            if instance_name not in dns_dict['dns_list']:
                logging.warning("Dns {} Not Found".format(instance_name))
            else:
                url = "{}/Dns/{}/{}".format(api_server_url, instance_name, cmd_type)
                config = dns_dict[instance_name]
                utils.post(url=url, config=config)
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

        elif curl_match:
            ipordns = curl_match.group(1)  # ip or damain name
            utils.exec_command(command=['curl', ipordns])
        else:
            print("Command does not match any valid command. Try 'help' for more information. ")


if __name__ == '__main__':
    main()