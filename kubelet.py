import re
import sys
import os
import yaml_loader
import entities
import string
import random
import etcd3


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


def create_suffix():
    res = ''.join(random.choices(string.ascii_letters +
                                 string.digits, k=10))
    res = '-' + res
    return res


def main():
    version = '1.0.0'
    # pods services和configs
    configs = {}
    pods = {}
    services = {}
    # etcd持久化存储
    etcd = etcd3.client()

    # 在修改pod状态时也要修改etcd内存储的pod状态
    def etcd_set_status(target_name, status):
        target_info = str(etcd.get(target_name)[0], 'UTF-8')
        target_string_list = target_info.split(' ')
        target_string_list[1] = status
        target_info = target_string_list[0]
        for index in range(1, len(target_string_list)):
            target_info += ' ' + target_string_list[index]
        etcd.put(target_name, target_info)

    # 恢复原数据
    for kvs in etcd.get_all_response().kvs:
        restart_pod_name = str(kvs.key, 'UTF-8')
        restart_pod_info = str(etcd.get(kvs.key)[0], 'UTF-8')
        string_list = restart_pod_info.split(' ')
        config = yaml_loader.load(string_list[0])
        config['status'] = string_list[1]
        configs[restart_pod_name] = config
        new_pods = []
        print(restart_pod_name)
        print(restart_pod_info)
        print(string_list)
        for i in range(2, len(string_list)):
            config['suffix'] = string_list[i]
            pod = entities.Pod(config, True)
            new_pods.append(pod)
        pods[restart_pod_name] = new_pods
    while True:
        cmd = input(">>")

        exit_match = re.fullmatch(r'exit', cmd.strip(), re.I)
        help_match = re.fullmatch(r'help', cmd.strip(), re.I)
        version_match = re.fullmatch(r'version', cmd.strip(), re.I)
        show_match = re.fullmatch(r'show (pods|services)', cmd.strip(), re.I)
        start_file_match = re.fullmatch(r'start -f ([a-zA-Z0-9:/\\_\-.]*yaml|yml)', cmd.strip(), re.I)
        normal_command_match = re.fullmatch(r'(start|stop|kill|restart|remove) *(pod|service) *([\w-]*)', cmd.strip(),
                                            re.I)
        # ###
        # if cmd == "test":
        #     for name in pods:
        #         the_pods = pods[name]
        #         for pod in the_pods:
        #             pod.cpu_monitor()
        #     continue
        # ###

        if exit_match:
            # 删除etcd全部kv
            for kvs in etcd.get_all_response().kvs:
                etcd.delete(kvs.key)
            break
        elif help_match:
            print_info()
        elif version_match:
            print("{} v{}".format('minik8s'.title(), version))
        elif show_match:
            object_type = show_match.group(1)
            if object_type == "pods":
                print("extant pods:\nname   status   volumn   containers_num")
                for name in pods:
                    print("{}   {}   {}   {}".format(name, pods[name][0].status(), pods[name][0].volumn(),
                                                     len(pods[name][0].contains())))
            elif object_type == "services":
                print("extant services:")
        elif start_file_match:
            file_path = start_file_match.group(1)
            if not os.path.isfile(file_path):
                print("file not exist")
                continue
            config = yaml_loader.load(file_path)
            if 'name' not in config:
                sys.stdout.write('yaml name is missing')
            if config.get('kind') == 'pod':
                name = config.get('name')
                # 检查pod是否已存在
                if name in pods:
                    print("pod:{} already exist".format(name))
                    continue
                # 创建pod并创建开启容器
                configs[name] = config
                pod_num = config['spec']['replicas']
                new_pods = []
                # etcd存储准备
                info = file_path + ' ' + str(entities.Status.RUNNING)
                for i in range(pod_num):
                    suffix = create_suffix()
                    config['suffix'] = suffix
                    pod = entities.Pod(config, False)
                    new_pods.append(pod)
                    info += ' ' + suffix
                etcd.put(name, info)
                # ###
                # config['suffix'] = create_suffix()
                # pod = entities.Pod(config, False)
                # new_pods.append(pod)
                # ###
                pods[name] = new_pods
                print('pod:{} created successfully'.format(name))
            elif config.get('kind') == 'service':
                # 创建service（检查重名）
                print('test')
            else:
                print("file content error")
        elif normal_command_match:
            cmd_type = normal_command_match.group(1)
            object_type = normal_command_match.group(2)
            object_name = normal_command_match.group(3)
            if object_type == 'service':
                raise NotImplementedError
            elif object_type == 'pod':
                the_pods = pods[object_name]
                for pod in the_pods:
                    getattr(pod, cmd_type)()
                if cmd_type == 'remove':
                    pods.pop(object_name)
                    configs.pop(object_name)
                if cmd_type == 'restart' or cmd_type == 'start':
                    etcd_set_status(object_name, 'Status.RUNNING')
                if cmd_type == 'kill':
                    etcd_set_status(object_name, 'Status.KILLED')
                if cmd_type == 'stop':
                    etcd_set_status(object_name, 'Status.STOPPED')
        else:
            print("Command does not match any valid command. Try 'help' for more information. ")


if __name__ == '__main__':
    main()
