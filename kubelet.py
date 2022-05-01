import re
import sys
import os
import yaml_loader
import entities


def main():
    version = '1.0.0'
    cmd = ""
    pods = {}
    services = {}
    while cmd != "exit":
        cmd = input(">>")
        # 删除前后空格和多余空格
        cmdparts = cmd.split(" ")
        # help
        if cmd == "help":
            sys.stdout.write("version                       show minik8s version\n")
            sys.stdout.write("show pods                      display extant pods\n")
            sys.stdout.write("show services              display extant services\n")
            sys.stdout.write("start -f filepath                  start container\n")
            sys.stdout.write("start pod/service name   start stopped pod/service\n")
            sys.stdout.write("stop pod/service name             stop pod/service\n")
            sys.stdout.write("kill pod/service name             kill pod/service\n")
            sys.stdout.write("restart pod/service name       restart pod/service\n")
            sys.stdout.write("remove pod/service name         remove pod/service\n")
            continue
        # version
        version_match = re.fullmatch(r'version', cmd.strip(), re.I)
        show_match = re.fullmatch(r'show (pods|services)', cmd.strip(), re.I)
        start_file_match = re.fullmatch(r'start -f ([a-zA-Z0-9:/\\_\-.]*yaml|yml)', cmd.strip(), re.I)
        normal_command_match = re.fullmatch(r'(start|stop|kill|restart|remove) *(pod|service) *(\w*)', cmd.strip(), re.I)
        if version_match:
            print("{} v{}".format('minik8s'.title(), version))
            continue
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
            config = yaml_loader.load(cmdparts[2])
            if 'name' not in config:
                sys.stdout.write('yaml name is missing')
            if config.get('kind') == 'pod':
                name = config.get('name')
                # 检查pod是否已存在
                if name in pods:
                    sys.stdout.write("pod:{} already exist\n".format(name))
                    continue
                # 创建pod并并创建开启容器
                pod = entities.Pod(config)
                pods[name] = pod
                sys.stdout.write('pod:{} created successfully\n'.format(name))
            elif config.get('kind') == 'service':
                # 创建service（检查重名）
                print('test')
            else:
                sys.stdout.write("file content error\n")
                continue
        elif normal_command_match:
            cmd_type = normal_command_match.group(1)
            object_type = normal_command_match.group(2)
            if object_type == 'service':
                raise NotImplementedError
            elif object_type == 'pod':
                pod = pods[cmdparts[2]]
                getattr(pod, cmd_type)()
        else:
            print("Command does not match any valid command. Try 'help' for more information. ")


if __name__ == '__main__':
    sys.exit(main())
