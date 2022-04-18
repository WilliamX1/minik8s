import re
import sys
import os
import yamlloader
import entities


def invalidcmd(err):
    sys.stdout.write(err + ",input \"help\" to get support\n")

def main():
    version = '1.0.0'
    cmd = ""
    command = ["show", "start", "stop", "kill", "restart", "remove"]
    pods = {}
    services = {}
    while cmd != "exit":
        cmd = input(">>")
        # 删除前后空格和多余空格
        cmd = cmd.strip()
        cmd = re.sub(' +', ' ', cmd)
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
        if cmd == "version":
            sys.stdout.write("{} v{}\n".format('minik8s'.title(), version))
            continue

        if len(cmdparts) > 3 or cmdparts[0] not in command:
            invalidcmd("invalid cmd")
            continue

        if cmdparts[0] == "show":
            if len(cmdparts) > 2:
                invalidcmd("too many parameters for show")
                continue
            if cmdparts[1] == "pods":
                ## 展示pods
                sys.stdout.write("extant pods:\n")
                sys.stdout.write("name   status   volumn   containers_num\n")
                for name in pods:
                    sys.stdout.write(
                        "{}   {}   {}   {}\n".format(pods[name].name(), pods[name].status(), pods[name].volumn(),
                                                     len(pods[name].contains())))

            elif cmdparts[1] == "services":
                ## 展示services
                sys.stdout.write("extant services:\n")

            else:
                invalidcmd("wrong parameter for show")
                continue

        elif cmdparts[0] == "start":
            if len(cmdparts) < 3:
                invalidcmd("too few parameters for start")
                continue
            elif cmdparts[1] == "-f":
                # 判断文件路径合法
                if not cmdparts[2].endswith(".yaml") and not cmdparts[2].endswith(".yml"):
                    sys.stdout.write("target is not a yaml file\n")
                    continue
                if not os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + '/' + cmdparts[2]):
                    sys.stdout.write("file not exist\n")
                    continue
                # 成功打开文件
                config = yamlloader.load(cmdparts[2])
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
                    ## 创建service（检查重名）
                    print('test')
                else:
                    sys.stdout.write("file content error\n")
                    continue
            elif cmdparts[1] == "pod":
                # 查找pod是否存在并判断状态是否为stopped
                if cmdparts[2] not in pods:
                    sys.stdout.write("pod:{} not exist\n".format(cmdparts[2]))
                    continue;
                pod = pods[cmdparts[2]]
                if pod.status() == entities.Status.RUNNING:
                    sys.stdout.write("pod:{} has already started\n".format(cmdparts[2]))
                    continue;
                if pod.status() == entities.Status.KILLED:
                    sys.stdout.write("pod:{} has already be killed\n".format(cmdparts[2]))
                    continue;
                # 暂停该pod中的所有容器
                pod.start()
                sys.stdout.write('pod:{} started successfully\n'.format(pod.name()))
                continue;
            elif cmdparts[1] == "service":
                ## 查找service是否存在并判断状态是否为stopped
                print("test")
            else:
                invalidcmd("wrong parameter for start")
                continue
        elif cmdparts[0] == "stop":
            if len(cmdparts) < 3:
                invalidcmd("too few parameters for stop")
                continue
            elif cmdparts[1] == "pod":
                # 查找pod是否存在并判断状态是否为running
                if cmdparts[2] not in pods:
                    sys.stdout.write("pod:{} not exist\n".format(cmdparts[2]))
                    continue;
                pod = pods[cmdparts[2]]
                if pod.status() == entities.Status.STOPPED:
                    sys.stdout.write("pod:{} has already stopped\n".format(cmdparts[2]))
                    continue;
                if pod.status() == entities.Status.KILLED:
                    sys.stdout.write("pod:{} has already be killed\n".format(cmdparts[2]))
                    continue;
                # 暂停该pod中的所有容器
                pod.stop()
                sys.stdout.write('pod:{} stopped successfully\n'.format(pod.name()))
                continue;
            elif cmdparts[1] == "service":
                ## 查找service是否存在并判断状态是否为running
                print("test")
            else:
                invalidcmd("wrong parameter for stop")
                continue
        elif cmdparts[0] == "kill":
            if len(cmdparts) < 3:
                invalidcmd("too few parameters for kill")
                continue
            elif cmdparts[1] == "pod":
                # 查找pod是否存在
                if cmdparts[2] not in pods:
                    sys.stdout.write("pod:{} not exist\n".format(cmdparts[2]))
                    continue;
                pod = pods[cmdparts[2]]
                if pod.status() == entities.Status.KILLED:
                    sys.stdout.write("pod:{} has already be killed\n".format(cmdparts[2]))
                    continue;
                # 杀死该pod中的所有容器
                pod.kill()
                sys.stdout.write('pod:{} be killed successfully\n'.format(pod.name()))
                continue;
            elif cmdparts[1] == "service":
                ## 查找service是否存在
                print("test")
            else:
                invalidcmd("wrong parameter for kill")
                continue
        elif cmdparts[0] == "restart":
            if len(cmdparts) < 3:
                invalidcmd("too few parameters for restart")
                continue
            elif cmdparts[1] == "pod":
                # 查找pod是否存在
                if cmdparts[2] not in pods:
                    sys.stdout.write("pod:{} not exist\n".format(cmdparts[2]))
                    continue;
                pod = pods[cmdparts[2]]
                if pod.status() == entities.Status.KILLED:
                    sys.stdout.write("pod:{} has already be killed\n".format(cmdparts[2]))
                    continue;
                # 重启该pod中的所有容器
                pod.restart()
                sys.stdout.write('pod:{} restarted successfully\n'.format(pod.name()))
                continue;
            elif cmdparts[1] == "service":
                ## 查找service是否存在并判断状态是否为running
                print("test")
            else:
                invalidcmd("wrong parameter for restart")
                continue
        elif cmdparts[0] == "remove":
            if len(cmdparts) < 3:
                invalidcmd("too few parameters for remove")
                continue
            elif cmdparts[1] == "pod":
                # 查找pod是否存在
                if cmdparts[2] not in pods:
                    sys.stdout.write("pod:{} not exist\n".format(cmdparts[2]))
                    continue;
                pod = pods[cmdparts[2]]
                if pod.status() == entities.Status.RUNNING:
                    pod.stop()
                # 删除该pod中的所有容器
                pod.remove()
                # 删除该pod
                pods.pop(pod.name())
                sys.stdout.write('pod:{} removed successfully\n'.format(pod.name()))
                continue;
            elif cmdparts[1] == "service":
                ## 查找service是否存在并判断状态是否为stopped
                print("test")
            else:
                invalidcmd("wrong parameter for remove")
                continue


if __name__ == '__main__':
    sys.exit(main())
