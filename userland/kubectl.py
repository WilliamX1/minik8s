import json
import logging
import re
import time

import requests
import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
sys.path.append(os.path.join(BASE_DIR, '../worker'))
import kubedns
import utils, const, yaml_loader
import kubeproxy
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
        show_match = re.fullmatch(r'show *(pods|services|replicasets|dns|nodes|functions)', cmd.strip(), re.I)
        start_file_match = re.fullmatch(r'start *-f *([a-zA-Z0-9:/\\_\-.]*yaml|yml)', cmd.strip(), re.I)
        pod_command_match = re.fullmatch(r'(start|remove) * pod *([\w-]*)', cmd.strip(), re.I)
        service_command_match = re.fullmatch(r'(update|restart|remove) * service *([\w-]*)', cmd.strip(), re.I)
        dns_command_match = re.fullmatch(r'(update|restart|remove) * dns *([\w-]*)', cmd.strip(), re.I)
        curl_match = re.fullmatch(r'curl * ([a-zA-Z0-9:/\\_\-.]*)', cmd.strip(), re.I)  # only used for test
        upload_python_match = re.fullmatch(r'upload *function *-f *([a-zA-Z0-9:/\\_\-.]*py)', cmd.strip(), re.I)
        upload_requirement_match = re.fullmatch(r'upload *function *([\w-]*) *-r *([a-zA-Z0-9:/\\_\-.]*txt)', cmd.strip(), re.I)
        start_function_match = re.fullmatch(r'start *function *([\w-]*)', cmd.strip(), re.I)

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
                    pod_config = pods_dict.get(pod_instance_name)
                    if pod_config:
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
            elif object_type == 'functions':
                # todo: test logic here
                functions_dict = utils.get_function_dict(api_server_url=api_server_url)
                tb = prettytable.PrettyTable()
                tb.field_names = ['name', 'status', 'requirement_status', 'created time']
                for function_name in functions_dict['functions_list']:
                    function_config = functions_dict.get(function_name)
                    if function_config:
                        created_time = int(time.time() - function_config['created_time'])
                        created_time = str(created_time // 60) + "m" + str(created_time % 60) + 's'
                        tb.add_row([function_name, function_config['status'], function_config['requirement_status'], created_time.strip()])
                print(tb)
            elif object_type == 'nodes':
                nodes_dict = utils.get_node_dict(api_server_url=api_server_url)
                tb = prettytable.PrettyTable()
                tb.field_names = ['name', 'status', 'last_receive_time']
                for node_instance_name in nodes_dict['nodes_list']:
                    node_config = nodes_dict.get(node_instance_name)
                    if node_config:
                        last_receive_time = int(time.time() - node_config['last_receive_time'])
                        last_receive_time = str(last_receive_time // 60) + "m" + str(last_receive_time % 60) + 's'
                        tb.add_row([node_instance_name, node_config['status'], last_receive_time.strip()])
                print(tb)
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
        elif upload_python_match:
            python_path = upload_python_match.group(1)
            if not os.path.isfile(python_path):
                print("file not exist")
                continue
            url = "{}/Function".format(api_server_url)
            module_name = None
            with open(python_path) as f:
                flag = 0
                for i in range(len(f.name) - 1, 0, -1):
                    if f.name[i] == '/':
                        module_name = f.name[i + 1: -3]
                        flag = 1
                        break
                if flag == 0:
                    module_name = f.name[:-3]
                content = f.read()
            assert module_name
            config: dict = yaml_loader.load(os.path.join(BASE_DIR, 'yaml_default', 'my_function.yaml'))
            config['name'] += module_name
            config['metadata']['labels']['module_name'] = module_name
            config['containers'][0]['name'] = module_name
            config['containers'][0]['image'] = "{}:latest".format(module_name)
            config['script_data'] = content

            print(config)
            r = requests.post(url=url, json=json.dumps(config))
        elif upload_requirement_match:
            module_name = upload_requirement_match.group(1)
            requirement_path = upload_requirement_match.group(2)
            if not os.path.isfile(requirement_path):
                print("file not exist")
                continue
            url = "{}/Function/{}/upload_requirement".format(api_server_url, module_name)
            with open(requirement_path) as f:
                content = f.read()
            r = requests.post(url=url, json=json.dumps({'requirement': content}))
            if r.status_code != 200:
                print("Function instance not found!")
        elif start_function_match:
            module_name = start_function_match.group(1)
            url = "{}/Function/{}/start".format(api_server_url, module_name)
            r = requests.post(url=url, json=json.dumps(dict()))
            if r.status_code != 200:
                print("Function instance not found!")
            else:
                print("Start successfully!")
        elif curl_match:
            ipordns = curl_match.group(1)  # ip or damain name
            utils.exec_command(command=['curl', ipordns])
        else:
            print("Command does not match any valid command. Try 'help' for more information. ")


if __name__ == '__main__':
    main()
