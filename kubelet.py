import re
import sys
import os
import yaml_loader
import entities

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
    pods = {}
    services = {}
    while True:
        cmd = input(">>")

        exit_match = re.fullmatch(r'exit', cmd.strip(), re.I)
        help_match = re.fullmatch(r'help', cmd.strip(), re.I)
        version_match = re.fullmatch(r'version', cmd.strip(), re.I)
        show_match = re.fullmatch(r'show (pods|services)', cmd.strip(), re.I)
        start_file_match = re.fullmatch(r'start -f ([a-zA-Z0-9:/\\_\-.]*yaml|yml)', cmd.strip(), re.I)
        normal_command_match = re.fullmatch(r'(start|stop|kill|restart|remove) *(pod|service) *(\w*)', cmd.strip(), re.I)

        if exit_match:
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
                    print("{}   {}   {}   {}".format(pods[name].name(), pods[name].status(), pods[name].volumn(),
                                                     len(pods[name].contains())))
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
                pod = entities.Pod(config)
                pods[name] = pod
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
                pod = pods[object_name]
                getattr(pod, cmd_type)()
        else:
            print("Command does not match any valid command. Try 'help' for more information. ")


if __name__ == '__main__':
    main()
