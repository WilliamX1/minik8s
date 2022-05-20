import time
import entities
import random


def monitor():
    # 监听pod的在状态，后面需要加入service
    second = 5
    while 1 == 1:
        time.sleep(second)
        # 获取kubelet中的pods和configs
        pods = {}
        configs = {}
        for name in pods:
            config = configs[name]
            for i in range(len(pods[name])):
                if pods[name][i].status() == entities.Status.KILLED:
                    # 存在pod副本被kill，删除旧的pod副本
                    pods[name][i].remove()
                    # 重启一个pod副本
                    config['suffix'] = pods[name][i].suffix()
                    pods[name][i] = entities.Pod(config, False)


# 随即负载均衡
def lb():
    # 获取service的一个pod的所有副本，随机返回一个
    the_pods = []
    return the_pods[random.randint(0, len(the_pods) - 1)]
